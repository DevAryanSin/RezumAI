import { useParams, Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { mockCandidates } from "@/lib/mockData";
import {
  ArrowLeft,
  Star,
  MapPin,
  Briefcase,
  Mail,
  Phone,
  Download,
  Eye,
  Calendar,
  Award,
  Code,
} from "lucide-react";
import { useState } from "react";
import { useToast } from "@/hooks/use-toast";

export default function CandidateProfile() {
  const { id } = useParams();
  const { toast } = useToast();
  const candidate = mockCandidates.find((c) => c.candidateId === id);
  const [newComment, setNewComment] = useState("");
  const [newTag, setNewTag] = useState("");

  if (!candidate) {
    return (
      <div className="flex min-h-screen items-center justify-center p-6">
        <Card className="p-12 text-center">
          <h2 className="mb-2 text-2xl font-bold text-foreground">Candidate not found</h2>
          <p className="mb-4 text-muted-foreground">The candidate you're looking for doesn't exist.</p>
          <Button asChild>
            <Link to="/candidates">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Candidates
            </Link>
          </Button>
        </Card>
      </div>
    );
  }

  const handleAddComment = () => {
    if (!newComment.trim()) return;
    toast({
      title: "Comment added",
      description: "Your comment has been saved.",
    });
    setNewComment("");
  };

  const handleAddTag = () => {
    if (!newTag.trim()) return;
    toast({
      title: "Tag added",
      description: `Tag "${newTag}" has been added.`,
    });
    setNewTag("");
  };

  return (
    <div className="min-h-screen p-6 lg:p-8">
      {/* Back button */}
      <Button variant="ghost" className="mb-6" asChild>
        <Link to="/candidates">
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Candidates
        </Link>
      </Button>

      {/* Header Card */}
      <Card className="mb-6 overflow-hidden">
        <div className="h-32 bg-gradient-to-r from-primary to-secondary" />
        <div className="relative px-6 pb-6">
          <div className="absolute -top-12 flex h-24 w-24 items-center justify-center rounded-full border-4 border-card bg-gradient-to-br from-primary to-secondary text-3xl font-bold text-white">
            {candidate.name.split(" ").map((n) => n[0]).join("")}
          </div>
          <div className="pt-16">
            <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
              <div>
                <h1 className="mb-1 text-3xl font-bold text-foreground">{candidate.name}</h1>
                <p className="mb-2 text-xl text-muted-foreground">{candidate.title}</p>
                <div className="flex flex-wrap gap-3 text-sm text-muted-foreground">
                  {candidate.email && (
                    <span className="flex items-center gap-1">
                      <Mail className="h-4 w-4" />
                      {candidate.email}
                    </span>
                  )}
                  {candidate.phone && (
                    <span className="flex items-center gap-1">
                      <Phone className="h-4 w-4" />
                      {candidate.phone}
                    </span>
                  )}
                  {candidate.location && (
                    <span className="flex items-center gap-1">
                      <MapPin className="h-4 w-4" />
                      {candidate.location}
                    </span>
                  )}
                </div>
              </div>
              <div className="flex gap-2">
                <Button variant="outline">
                  <Download className="mr-2 h-4 w-4" />
                  Download
                </Button>
                <Button variant="outline">
                  <Eye className="mr-2 h-4 w-4" />
                  Redact PII
                </Button>
                <Button>
                  <Star className={candidate.shortlisted ? "mr-2 h-4 w-4 fill-current" : "mr-2 h-4 w-4"} />
                  {candidate.shortlisted ? "Shortlisted" : "Shortlist"}
                </Button>
              </div>
            </div>
          </div>
        </div>
      </Card>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Main content */}
        <div className="space-y-6 lg:col-span-2">
          {/* Match Score */}
          {candidate.score && (
            <Card className="p-6">
              <h2 className="mb-4 text-lg font-semibold text-foreground">Match Score</h2>
              <div className="flex items-center gap-4">
                <div className="flex h-20 w-20 items-center justify-center rounded-full border-4 border-primary text-3xl font-bold text-primary">
                  {candidate.score}
                </div>
                <div className="flex-1">
                  <div className="mb-2 h-2 rounded-full bg-muted">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-primary to-secondary transition-all animate-score-fill"
                      style={{ "--score-width": `${candidate.score}%` } as React.CSSProperties}
                    />
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Excellent match for the position based on skills and experience
                  </p>
                </div>
              </div>
            </Card>
          )}

          {/* Skills */}
          <Card className="p-6">
            <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-foreground">
              <Code className="h-5 w-5" />
              Skills & Technologies
            </h2>
            <div className="flex flex-wrap gap-2">
              {candidate.skills.map((skill, idx) => (
                <Badge key={idx} variant={candidate.highlights?.includes(skill) ? "default" : "secondary"}>
                  {skill}
                </Badge>
              ))}
            </div>
          </Card>

          {/* Work Experience */}
          {candidate.workExperience && candidate.workExperience.length > 0 && (
            <Card className="p-6">
              <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-foreground">
                <Briefcase className="h-5 w-5" />
                Work Experience
              </h2>
              <div className="space-y-6">
                {candidate.workExperience.map((exp, idx) => (
                  <div key={idx} className="relative pl-6 before:absolute before:left-0 before:top-2 before:h-full before:w-px before:bg-border last:before:hidden">
                    <div className="absolute left-0 top-2 h-2 w-2 -translate-x-0.5 rounded-full bg-primary" />
                    <div className="mb-1 flex flex-wrap items-start justify-between gap-2">
                      <div>
                        <h3 className="font-semibold text-foreground">{exp.title}</h3>
                        <p className="text-sm text-muted-foreground">{exp.company}</p>
                      </div>
                      <span className="flex items-center gap-1 text-sm text-muted-foreground">
                        <Calendar className="h-4 w-4" />
                        {exp.duration}
                      </span>
                    </div>
                    <ul className="mb-2 list-inside list-disc space-y-1 text-sm text-muted-foreground">
                      {exp.description.map((desc, i) => (
                        <li key={i}>{desc}</li>
                      ))}
                    </ul>
                    {exp.technologies && (
                      <div className="flex flex-wrap gap-1">
                        {exp.technologies.map((tech, i) => (
                          <Badge key={i} variant="outline" className="text-xs">
                            {tech}
                          </Badge>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* Education */}
          {candidate.education && candidate.education.length > 0 && (
            <Card className="p-6">
              <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-foreground">
                <Award className="h-5 w-5" />
                Education
              </h2>
              <div className="space-y-4">
                {candidate.education.map((edu, idx) => (
                  <div key={idx}>
                    <h3 className="font-semibold text-foreground">{edu.degree}</h3>
                    <p className="text-sm text-muted-foreground">
                      {edu.institution} • {edu.year}
                      {edu.gpa && ` • GPA: ${edu.gpa}`}
                    </p>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* Evidence Snippets */}
          {candidate.snippets && candidate.snippets.length > 0 && (
            <Card className="p-6">
              <h2 className="mb-4 text-lg font-semibold text-foreground">Evidence & Highlights</h2>
              <div className="space-y-3">
                {candidate.snippets.map((snippet, idx) => (
                  <div key={idx} className="rounded-lg border border-border bg-accent/30 p-4">
                    <p className="mb-2 text-sm text-foreground">"{snippet.text}"</p>
                    <p className="text-xs text-muted-foreground">Source: {snippet.source}</p>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Quick Stats */}
          <Card className="p-6">
            <h3 className="mb-4 text-sm font-semibold text-foreground">Quick Stats</h3>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Experience</span>
                <span className="font-medium text-foreground">{candidate.experienceYears} years</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Current Company</span>
                <span className="font-medium text-foreground">{candidate.currentCompany}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Skills</span>
                <span className="font-medium text-foreground">{candidate.skills.length}</span>
              </div>
            </div>
          </Card>

          {/* Tags */}
          <Card className="p-6">
            <h3 className="mb-4 text-sm font-semibold text-foreground">Tags</h3>
            <div className="mb-3 flex flex-wrap gap-2">
              {candidate.tags?.map((tag, idx) => (
                <Badge key={idx} variant="secondary">
                  #{tag}
                </Badge>
              ))}
            </div>
            <div className="flex gap-2">
              <Input
                placeholder="Add tag..."
                value={newTag}
                onChange={(e) => setNewTag(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleAddTag()}
              />
              <Button size="sm" onClick={handleAddTag}>
                Add
              </Button>
            </div>
          </Card>

          {/* Comments */}
          <Card className="p-6">
            <h3 className="mb-4 text-sm font-semibold text-foreground">Comments</h3>
            {candidate.comments && candidate.comments.length > 0 && (
              <div className="mb-4 space-y-3">
                {candidate.comments.map((comment) => (
                  <div key={comment.id} className="rounded-lg border border-border p-3">
                    <div className="mb-1 flex items-center justify-between text-xs">
                      <span className="font-medium text-foreground">{comment.recruiterName}</span>
                      <span className="text-muted-foreground">
                        {new Date(comment.timestamp).toLocaleDateString()}
                      </span>
                    </div>
                    <p className="text-sm text-muted-foreground">{comment.comment}</p>
                  </div>
                ))}
              </div>
            )}
            <div className="space-y-2">
              <Label htmlFor="comment">Add Comment</Label>
              <Textarea
                id="comment"
                placeholder="Write your thoughts about this candidate..."
                value={newComment}
                onChange={(e) => setNewComment(e.target.value)}
                rows={3}
              />
              <Button className="w-full" onClick={handleAddComment}>
                Add Comment
              </Button>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
