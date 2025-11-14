import { Card } from "@/components/ui/card";
import UploadDropzone from "@/components/upload/UploadDropzone";
import { FileText, CheckCircle2 } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

export default function Upload() {
  const { toast } = useToast();

  const handleUpload = (files: File[]) => {
    toast({
      title: "Upload started",
      description: `Uploading ${files.length} file(s)...`,
    });
  };

  return (
    <div className="min-h-screen p-6 lg:p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="mb-2 text-3xl font-bold text-foreground">Upload Resumes</h1>
        <p className="text-muted-foreground">
          Upload PDF resumes to automatically parse and index candidates.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Upload area */}
        <div className="lg:col-span-2">
          <UploadDropzone onUpload={handleUpload} />
        </div>

        {/* Info sidebar */}
        <div className="space-y-4">
          <Card className="p-6">
            <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold text-foreground">
              <FileText className="h-5 w-5 text-primary" />
              Supported Formats
            </h3>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li className="flex items-start gap-2">
                <CheckCircle2 className="mt-0.5 h-4 w-4 text-success flex-shrink-0" />
                <span>PDF documents (.pdf)</span>
              </li>
              {/* <li className="flex items-start gap-2">
                <CheckCircle2 className="mt-0.5 h-4 w-4 text-success flex-shrink-0" />
                <span>Microsoft Word (.docx)</span>
              </li> */}
              <li className="flex items-start gap-2">
                <CheckCircle2 className="mt-0.5 h-4 w-4 text-success flex-shrink-0" />
                <span>Maximum file size: 10MB</span>
              </li>
            </ul>
          </Card>

          <Card className="p-6">
            <h3 className="mb-4 text-sm font-semibold text-foreground">What We Extract</h3>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li className="flex items-start gap-2">
                <div className="mt-1 h-1.5 w-1.5 rounded-full bg-primary flex-shrink-0" />
                <span>Contact information</span>
              </li>
              <li className="flex items-start gap-2">
                <div className="mt-1 h-1.5 w-1.5 rounded-full bg-primary flex-shrink-0" />
                <span>Work experience & timeline</span>
              </li>
              <li className="flex items-start gap-2">
                <div className="mt-1 h-1.5 w-1.5 rounded-full bg-primary flex-shrink-0" />
                <span>Skills & technologies</span>
              </li>
              <li className="flex items-start gap-2">
                <div className="mt-1 h-1.5 w-1.5 rounded-full bg-primary flex-shrink-0" />
                <span>Education & certifications</span>
              </li>
              <li className="flex items-start gap-2">
                <div className="mt-1 h-1.5 w-1.5 rounded-full bg-primary flex-shrink-0" />
                <span>Projects & achievements</span>
              </li>
            </ul>
          </Card>

          <Card className="border-secondary/20 bg-secondary/5 p-6">
            <h3 className="mb-2 text-sm font-semibold text-foreground">Privacy & Security</h3>
            <p className="text-sm text-muted-foreground">
              All uploaded resumes are encrypted and processed securely. PII redaction is available
              for sensitive information.
            </p>
          </Card>
        </div>
      </div>
    </div>
  );
}
