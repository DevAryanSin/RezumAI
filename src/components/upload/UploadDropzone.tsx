import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { Upload, FileText, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { UploadStatus } from "@/types/candidate";

interface UploadDropzoneProps {
  onUpload: (files: File[]) => void;
  acceptedTypes?: string[];
  maxSizeMB?: number;
  className?: string;
}

export default function UploadDropzone({
  onUpload,
  acceptedTypes = [".pdf", ".docx"],
  maxSizeMB = 10,
  className,
}: UploadDropzoneProps) {
  const [uploadQueue, setUploadQueue] = useState<UploadStatus[]>([]);

  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      const newUploads: UploadStatus[] = acceptedFiles.map((file, idx) => ({
        uploadId: `upload_${Date.now()}_${idx}`,
        filename: file.name,
        status: "uploading",
        progress: 0,
      }));

      setUploadQueue((prev) => [...prev, ...newUploads]);

      // Simulate upload progress
      newUploads.forEach((upload, idx) => {
        const interval = setInterval(() => {
          setUploadQueue((prev) =>
            prev.map((u) => {
              if (u.uploadId === upload.uploadId) {
                if (u.progress >= 100) {
                  clearInterval(interval);
                  setTimeout(() => {
                    setUploadQueue((prev2) =>
                      prev2.map((u2) =>
                        u2.uploadId === upload.uploadId
                          ? { ...u2, status: "parsing" as const }
                          : u2
                      )
                    );
                    setTimeout(() => {
                      setUploadQueue((prev3) =>
                        prev3.map((u3) =>
                          u3.uploadId === upload.uploadId
                            ? {
                                ...u3,
                                status: "parsed" as const,
                                candidateId: `c_${Date.now()}_${idx}`,
                              }
                            : u3
                        )
                      );
                    }, 2000);
                  }, 500);
                  return { ...u, progress: 100, status: "uploaded" as const };
                }
                return { ...u, progress: u.progress + 10 };
              }
              return u;
            })
          );
        }, 200);
      });

      onUpload(acceptedFiles);
    },
    [onUpload]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: acceptedTypes.reduce((acc, type) => ({ ...acc, [type]: [] }), {}),
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

  const getStatusText = (status: UploadStatus["status"]) => {
    switch (status) {
      case "uploading":
        return "Uploading...";
      case "uploaded":
        return "Uploaded";
      case "parsing":
        return "Parsing resume...";
      case "parsed":
        return "Ready";
      case "error":
        return "Error";
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
          isDragActive
            ? "border-primary bg-primary/5 scale-[1.02]"
            : "border-border hover:border-primary hover:bg-accent"
        )}
      >
        <input {...getInputProps()} />
        <Upload className={cn("mb-4 h-12 w-12", isDragActive ? "text-primary" : "text-muted-foreground")} />
        <p className="mb-2 text-lg font-semibold text-foreground">
          {isDragActive ? "Drop files here" : "Drag & drop resumes here"}
        </p>
        <p className="mb-4 text-sm text-muted-foreground">or click to browse</p>
        <p className="text-xs text-muted-foreground">
          Supports {acceptedTypes.join(", ")} • Max {maxSizeMB}MB
        </p>
      </div>

      {/* Upload queue */}
      {uploadQueue.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-sm font-semibold text-foreground">Upload Queue</h3>
          {uploadQueue.map((upload) => (
            <div
              key={upload.uploadId}
              className="flex items-center gap-3 rounded-lg border border-border bg-card p-4"
            >
              <FileText className="h-8 w-8 text-muted-foreground flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <div className="mb-1 flex items-center justify-between">
                  <p className="truncate text-sm font-medium text-foreground">{upload.filename}</p>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6 flex-shrink-0"
                    onClick={() => removeFromQueue(upload.uploadId)}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
                {upload.status === "uploading" && (
                  <Progress value={upload.progress} className="mb-1" />
                )}
                <div className="flex items-center gap-2">
                  <div className={cn("h-2 w-2 rounded-full", getStatusColor(upload.status))} />
                  <span className="text-xs text-muted-foreground">{getStatusText(upload.status)}</span>
                  {upload.candidateId && (
                    <a
                      href={`/candidate/${upload.candidateId}`}
                      className="ml-auto text-xs text-primary hover:underline"
                    >
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
