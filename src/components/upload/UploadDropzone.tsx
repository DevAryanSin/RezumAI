import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { Upload, FileText, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import type { UploadStatus } from "@/types/candidate";

interface UploadDropzoneProps {
  onUpload: (files: File[]) => void; // legacy callback (kept for compatibility)
  recruiterId?: string; // pass if you want dropzone to upload directly
  batchName?: string; // pass if you want dropzone to upload directly
  acceptedTypes?: string[]; // extensions like [".pdf", ".docx"]
  maxSizeMB?: number;
  className?: string;
}

// make sure this is in your file
type InternalUpload = {
  uploadId: string;
  filename: string;
  status: "uploading" | "uploaded" | "parsing" | "parsed" | "error";
  progress: number;
  candidateId?: string;
  errorMessage?: string;
};

export default function UploadDropzone({
  onUpload,
  recruiterId,
  batchName,
  acceptedTypes = [".pdf", ".docx"],
  maxSizeMB = 10,
  className,
}: UploadDropzoneProps) {
  const [uploadQueue, setUploadQueue] = useState<InternalUpload[]>([]);

  // build accept map for react-dropzone
  const acceptMap = acceptedTypes.reduce<Record<string, string[]>>((acc, ext) => {
    const e = ext.toLowerCase();
    if (e === ".pdf") acc["application/pdf"] = [".pdf"];
    else if (e === ".docx")
      acc["application/vnd.openxmlformats-officedocument.wordprocessingml.document"] = [".docx"];
    else acc[e] = [ext];
    return acc;
  }, {});

  const updateQueue = (uploadId: string, patch: Partial<InternalUpload>) =>
    setUploadQueue((prev) => prev.map((u) => (u.uploadId === uploadId ? { ...u, ...patch } : u)));

  const uploadFileToServer = useCallback(
  (file: File, uploadId: string) =>
    new Promise<void>((resolve) => {
      if (!recruiterId || !batchName) {
        resolve();
        return;
      }

      const xhr = new XMLHttpRequest();
      xhr.open("POST", "/upload_resume", true);

      xhr.upload.onprogress = (ev) => {
        if (ev.lengthComputable) {
          const pct = Math.round((ev.loaded / ev.total) * 100);
          updateQueue(uploadId, { progress: pct, status: "uploading" });
        }
      };

      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          updateQueue(uploadId, { progress: 100, status: "uploaded" });

          // simulate parsing
          setTimeout(() => updateQueue(uploadId, { status: "parsing" }), 300);
          setTimeout(() => {
            updateQueue(uploadId, {
              status: "parsed",
              candidateId: `c_${Date.now()}`,
              progress: 100,
            });
            resolve();
          }, 1700);

        } else if (xhr.status === 409) {
          updateQueue(uploadId, {
            status: "error",
            errorMessage: "A file with this name already exists in this batch.",
            progress: 0,
          });
          resolve();

        } else {
          const msg = xhr.responseText || xhr.statusText || `Upload failed (${xhr.status})`;
          updateQueue(uploadId, { status: "error", errorMessage: msg, progress: 0 });
          resolve();
        }
      };

      xhr.onerror = () => {
        updateQueue(uploadId, {
          status: "error",
          errorMessage: "Network error",
          progress: 0,
        });
        resolve();
      };

      const fd = new FormData();
      fd.append("recruiter_id", recruiterId);
      fd.append("branch_id", batchName);
      fd.append("recruiter_uuid", recruiterId);
      fd.append("batch_name", batchName);
      fd.append("original_filename", file.name);
      fd.append("file", file, file.name);

      xhr.send(fd);
    }),
  [recruiterId, batchName] // dependencies stay stable
);


  const onDrop = useCallback(
  (acceptedFiles: File[]) => {
    const timestamp = Date.now();

    // declare newUploads with the explicit InternalUpload[] type
    const newUploads: InternalUpload[] = acceptedFiles.map((file, idx) => ({
      uploadId: `upload_${timestamp}_${idx}`,
      filename: file.name,
      status: "uploading",
      progress: 0,
    }));

    // append typed array to queue
    setUploadQueue((prev) => [...prev, ...newUploads]);

    if (recruiterId && batchName) {
      (async () => {
        for (let i = 0; i < acceptedFiles.length; i++) {
          await uploadFileToServer(acceptedFiles[i], newUploads[i].uploadId);
        }
      })();
    } else {
      onUpload(acceptedFiles);
    }
  },
  [uploadFileToServer, recruiterId, batchName, onUpload]
);



  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: acceptMap,
    maxSize: maxSizeMB * 1024 * 1024,
  });

  const removeFromQueue = (uploadId: string) => {
    setUploadQueue((prev) => prev.filter((u) => u.uploadId !== uploadId));
  };

  const getStatusColor = (status: UploadStatus["status"]) => {
    switch (status) {
      case "uploading":
      case "uploaded":
        return "bg-primary";
      case "parsing":
        return "bg-warning";
      case "parsed":
        return "bg-success";
      case "error":
        return "bg-destructive";
      default:
        return "bg-muted";
    }
  };

  const getStatusText = (u: InternalUpload) => {
    switch (u.status) {
      case "uploading":
        return `Uploading... ${u.progress}%`;
      case "uploaded":
        return "Uploaded";
      case "parsing":
        return "Parsing resume...";
      case "parsed":
        return "Ready";
      case "error":
        return u.errorMessage || "Error";
      default:
        return "";
    }
  };

  return (
    <div className={cn("space-y-6", className)}>
      {/* Dropzone */}
      <div
        {...getRootProps()}
        className={cn(
          "flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-12 transition-all",
          isDragActive ? "border-primary bg-primary/5 scale-[1.02]" : "border-border hover:border-primary hover:bg-accent"
        )}
      >
        <input {...getInputProps()} />
        <Upload className={cn("mb-4 h-12 w-12", isDragActive ? "text-primary" : "text-muted-foreground")} />
        <p className="mb-2 text-lg font-semibold text-foreground">{isDragActive ? "Drop files here" : "Drag & drop resumes here"}</p>
        <p className="mb-4 text-sm text-muted-foreground">or click to browse</p>
        <p className="text-xs text-muted-foreground">Supports {acceptedTypes.join(", ")} • Max {maxSizeMB}MB</p>
      </div>

      {/* Upload queue */}
      {uploadQueue.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-sm font-semibold text-foreground">Upload Queue</h3>
          {uploadQueue.map((upload) => (
            <div key={upload.uploadId} className="flex items-center gap-3 rounded-lg border border-border bg-card p-4">
              <FileText className="h-8 w-8 text-muted-foreground flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <div className="mb-1 flex items-center justify-between">
                  <p className="truncate text-sm font-medium text-foreground">{upload.filename}</p>
                  <Button variant="ghost" size="icon" className="h-6 w-6 flex-shrink-0" onClick={() => removeFromQueue(upload.uploadId)}>
                    <X className="h-4 w-4" />
                  </Button>
                </div>

                {upload.status === "uploading" && <Progress value={upload.progress} className="mb-1" />}

                <div className="flex items-center gap-2">
                  <div className={cn("h-2 w-2 rounded-full", getStatusColor(upload.status))} />
                  <span className="text-xs text-muted-foreground">{getStatusText(upload)}</span>
                  {upload.candidateId && (
                    <a href={`/candidate/${upload.candidateId}`} className="ml-auto text-xs text-primary hover:underline">
                      View candidate →
                    </a>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
