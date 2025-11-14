import { Card } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Shield, Database, Zap, Eye } from "lucide-react";
import { useState } from "react";
import { useToast } from "@/hooks/use-toast";

export default function Settings() {
  const { toast } = useToast();
  const [settings, setSettings] = useState({
    piiRedaction: true,
    autoRetention: false,
    retentionDays: 90,
    agoraEnabled: false,
  });

  const handleSave = () => {
    toast({
      title: "Settings saved",
      description: "Your preferences have been updated successfully.",
    });
  };

  return (
    <div className="min-h-screen p-6 lg:p-8">
      <div className="mx-auto max-w-4xl">
        {/* Header */}
        <div className="mb-8">
          <h1 className="mb-2 text-3xl font-bold text-foreground">Settings</h1>
          <p className="text-muted-foreground">
            Manage your recruitment platform preferences and integrations
          </p>
        </div>

        <div className="space-y-6">
          {/* Privacy & PII */}
          <Card className="p-6">
            <div className="mb-6 flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                <Shield className="h-5 w-5 text-primary" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-foreground">Privacy & PII Protection</h2>
                <p className="text-sm text-muted-foreground">
                  Control how sensitive candidate information is handled
                </p>
              </div>
            </div>

            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="pii-redaction">PII Redaction</Label>
                  <p className="text-sm text-muted-foreground">
                    Automatically redact email addresses and phone numbers from candidate views
                  </p>
                </div>
                <Switch
                  id="pii-redaction"
                  checked={settings.piiRedaction}
                  onCheckedChange={(checked) =>
                    setSettings({ ...settings, piiRedaction: checked })
                  }
                />
              </div>

              <div className="rounded-lg border border-border bg-muted/30 p-4">
                <h3 className="mb-2 text-sm font-medium text-foreground">Protected Fields</h3>
                <div className="flex flex-wrap gap-2">
                  <div className="rounded-md bg-card px-2 py-1 text-xs text-foreground">
                    Email Address
                  </div>
                  <div className="rounded-md bg-card px-2 py-1 text-xs text-foreground">
                    Phone Number
                  </div>
                  <div className="rounded-md bg-card px-2 py-1 text-xs text-foreground">
                    Home Address
                  </div>
                  <div className="rounded-md bg-card px-2 py-1 text-xs text-foreground">
                    Date of Birth
                  </div>
                </div>
              </div>
            </div>
          </Card>

          {/* Data Retention */}
          <Card className="p-6">
            <div className="mb-6 flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-secondary/10">
                <Database className="h-5 w-5 text-secondary" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-foreground">Data Retention Policy</h2>
                <p className="text-sm text-muted-foreground">
                  Automatically manage candidate data lifecycle
                </p>
              </div>
            </div>

            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="auto-retention">Auto-delete old candidates</Label>
                  <p className="text-sm text-muted-foreground">
                    Automatically remove candidate data after specified period
                  </p>
                </div>
                <Switch
                  id="auto-retention"
                  checked={settings.autoRetention}
                  onCheckedChange={(checked) =>
                    setSettings({ ...settings, autoRetention: checked })
                  }
                />
              </div>

              {settings.autoRetention && (
                <div className="space-y-2">
                  <Label htmlFor="retention-days">Retention Period (days)</Label>
                  <Input
                    id="retention-days"
                    type="number"
                    value={settings.retentionDays}
                    onChange={(e) =>
                      setSettings({ ...settings, retentionDays: parseInt(e.target.value) })
                    }
                    min={30}
                    max={365}
                  />
                  <p className="text-xs text-muted-foreground">
                    Candidates will be automatically deleted {settings.retentionDays} days after
                    upload
                  </p>
                </div>
              )}
            </div>
          </Card>

          {/* Agora Integration */}
          <Card className="p-6">
            <div className="mb-6 flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-info/10">
                <Zap className="h-5 w-5 text-info" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-foreground">Agora Voice Integration</h2>
                <p className="text-sm text-muted-foreground">
                  Enable real-time voice conversations with the AI assistant
                </p>
              </div>
            </div>

            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="agora-enabled">Enable Voice Chat</Label>
                  <p className="text-sm text-muted-foreground">
                    Talk to the AI assistant using voice commands
                  </p>
                </div>
                <Switch
                  id="agora-enabled"
                  checked={settings.agoraEnabled}
                  onCheckedChange={(checked) =>
                    setSettings({ ...settings, agoraEnabled: checked })
                  }
                />
              </div>

              {settings.agoraEnabled && (
                <div className="rounded-lg border border-border bg-accent/30 p-4">
                  <div className="mb-3 flex items-center gap-2">
                    <Eye className="h-4 w-4 text-primary" />
                    <span className="text-sm font-medium text-foreground">Configuration</span>
                  </div>
                  <div className="space-y-3">
                    <div>
                      <Label htmlFor="agora-app-id" className="text-xs">
                        Agora App ID
                      </Label>
                      <Input id="agora-app-id" placeholder="Enter your Agora App ID" />
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Voice transcripts will be automatically integrated into chat history
                    </p>
                  </div>
                </div>
              )}
            </div>
          </Card>

          {/* Save button */}
          <div className="flex justify-end">
            <Button size="lg" onClick={handleSave}>
              Save Settings
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
