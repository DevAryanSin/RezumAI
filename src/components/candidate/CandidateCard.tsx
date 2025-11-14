import { Candidate } from "@/types/candidate";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Star, MapPin, Briefcase, ExternalLink } from "lucide-react";
import { cn } from "@/lib/utils";
import { Link } from "react-router-dom";
import { useEffect, useState } from "react";

interface CandidateCardProps {
  candidate: Candidate;
  onShortlist?: (id: string) => void;
  className?: string;
}

export default function CandidateCard({ candidate, onShortlist, className }: CandidateCardProps) {
  const [animatedScore, setAnimatedScore] = useState(0);
  const score = candidate.score || 0;

  useEffect(() => {
    const timer = setTimeout(() => {
      const interval = setInterval(() => {
        setAnimatedScore((prev) => {
          if (prev >= score) {
            clearInterval(interval);
            return score;
          }
          return prev + 1;
        });
      }, 15);
      return () => clearInterval(interval);
    }, 100);
    return () => clearTimeout(timer);
  }, [score]);

  const getScoreColor = (score: number) => {
    if (score >= 90) return "text-secondary";
    if (score >= 75) return "text-primary";
    if (score >= 60) return "text-warning";
    return "text-muted-foreground";
  };

  return (
    <Card className={cn("group relative overflow-hidden transition-all hover:shadow-lg", className)}>
      <div className="absolute right-0 top-0 h-24 w-24 translate-x-8 -translate-y-8 rounded-full bg-gradient-to-br from-primary/10 to-secondary/10 blur-2xl transition-transform group-hover:scale-150" />
      
      <div className="relative p-6">
        {/* Header */}
        <div className="mb-4 flex items-start justify-between">
          <div className="flex-1">
            <Link 
              to={`/candidate/${candidate.candidateId}`}
              className="group/link inline-block"
            >
              <h3 className="text-lg font-semibold text-foreground group-hover/link:text-primary transition-colors">
                {candidate.name}
              </h3>
            </Link>
            <p className="text-sm text-muted-foreground">{candidate.title}</p>
            <div className="mt-2 flex flex-wrap gap-2 text-xs text-muted-foreground">
              <span className="flex items-center gap-1">
                <Briefcase className="h-3 w-3" />
                {candidate.currentCompany}
              </span>
              {candidate.location && (
                <span className="flex items-center gap-1">
                  <MapPin className="h-3 w-3" />
                  {candidate.location}
                </span>
              )}
            </div>
          </div>
          
          {/* Score badge */}
          {candidate.score !== undefined && (
            <div className="flex flex-col items-center gap-1">
              <div className={cn(
                "flex h-16 w-16 items-center justify-center rounded-full border-4 border-current font-bold transition-all",
                getScoreColor(score)
              )}>
                <span className="text-2xl">{animatedScore}</span>
              </div>
              <span className="text-xs text-muted-foreground">Match</span>
            </div>
          )}
        </div>

        {/* Skills */}
        <div className="mb-4 flex flex-wrap gap-2">
          {candidate.skills.slice(0, 5).map((skill, idx) => (
            <Badge 
              key={idx} 
              variant={candidate.highlights?.includes(skill) ? "default" : "secondary"}
              className="text-xs"
            >
              {skill}
            </Badge>
          ))}
          {candidate.skills.length > 5 && (
            <Badge variant="outline" className="text-xs">
              +{candidate.skills.length - 5} more
            </Badge>
          )}
        </div>

        {/* Experience snippet */}
        {candidate.snippets && candidate.snippets.length > 0 && (
          <div className="mb-4 space-y-2">
            {candidate.snippets.slice(0, 2).map((snippet, idx) => (
              <p key={idx} className="text-sm text-muted-foreground line-clamp-2">
                "{snippet.text}"
              </p>
            ))}
          </div>
        )}

        {/* Experience years */}
        <div className="mb-4 text-sm text-muted-foreground">
          <strong className="text-foreground">{candidate.experienceYears}</strong> years of experience
        </div>

        {/* Tags */}
        {candidate.tags && candidate.tags.length > 0 && (
          <div className="mb-4 flex flex-wrap gap-1">
            {candidate.tags.map((tag, idx) => (
              <Badge key={idx} variant="outline" className="text-xs">
                #{tag}
              </Badge>
            ))}
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-2">
          <Button
            variant={candidate.shortlisted ? "default" : "outline"}
            size="sm"
            onClick={() => onShortlist?.(candidate.candidateId)}
            className="flex-1"
          >
            <Star className={cn("mr-2 h-4 w-4", candidate.shortlisted && "fill-current")} />
            {candidate.shortlisted ? "Shortlisted" : "Shortlist"}
          </Button>
          <Button variant="outline" size="sm" asChild>
            <Link to={`/candidate/${candidate.candidateId}`}>
              <ExternalLink className="mr-2 h-4 w-4" />
              View
            </Link>
          </Button>
        </div>
      </div>
    </Card>
  );
}
