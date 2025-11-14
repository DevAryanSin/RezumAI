import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Search, Users, Star, Clock, TrendingUp } from "lucide-react";
import { mockKPIs, mockCandidates } from "@/lib/mockData";
import CandidateCard from "@/components/candidate/CandidateCard";
import { Link } from "react-router-dom";
import { useState } from "react";

export default function Dashboard() {
  const [searchQuery, setSearchQuery] = useState("");

  const kpiCards = [
    {
      title: "Total Candidates",
      value: mockKPIs.totalCandidates,
      icon: Users,
      color: "text-primary",
      bgColor: "bg-primary/10",
    },
    {
      title: "Shortlisted",
      value: mockKPIs.shortlisted,
      icon: Star,
      color: "text-secondary",
      bgColor: "bg-secondary/10",
    },
    {
      title: "Pending Review",
      value: mockKPIs.reviewsPending,
      icon: Clock,
      color: "text-warning",
      bgColor: "bg-warning/10",
    },
    {
      title: "Avg Match Score",
      value: `${mockKPIs.averageMatchScore}%`,
      icon: TrendingUp,
      color: "text-info",
      bgColor: "bg-info/10",
    },
  ];

  return (
    <div className="min-h-screen p-6 lg:p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="mb-2 text-3xl font-bold text-foreground">Welcome back!</h1>
        <p className="text-muted-foreground">
          Here's what's happening with your recruitment pipeline today.
        </p>
      </div>

      {/* KPIs */}
      <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {kpiCards.map((kpi, idx) => (
          <Card key={idx} className="group overflow-hidden transition-all hover:shadow-lg animate-fade-in" style={{ animationDelay: `${idx * 100}ms` }}>
            <div className="relative p-6">
              <div className={`absolute right-4 top-4 rounded-lg ${kpi.bgColor} p-3 transition-transform group-hover:scale-110`}>
                <kpi.icon className={`h-5 w-5 ${kpi.color}`} />
              </div>
              <div>
                <p className="mb-1 text-sm text-muted-foreground">{kpi.title}</p>
                <p className="text-3xl font-bold text-foreground">{kpi.value}</p>
              </div>
            </div>
          </Card>
        ))}
      </div>

      {/* Quick Search */}
      <Card className="mb-8 p-6">
        <h2 className="mb-4 text-lg font-semibold text-foreground">Quick Search</h2>
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search candidates by skills, experience, location..."
              className="pl-10"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <Button asChild>
            <Link to={`/candidates?q=${encodeURIComponent(searchQuery)}`}>
              Search
            </Link>
          </Button>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <span className="text-sm text-muted-foreground">Quick filters:</span>
          <Button variant="outline" size="sm" asChild>
            <Link to="/candidates?filter=backend">Backend Developers</Link>
          </Button>
          <Button variant="outline" size="sm" asChild>
            <Link to="/candidates?filter=kubernetes">Kubernetes Experts</Link>
          </Button>
          <Button variant="outline" size="sm" asChild>
            <Link to="/candidates?filter=senior">Senior Engineers</Link>
          </Button>
        </div>
      </Card>

      {/* Top Matches */}
      <div className="mb-8">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-foreground">Top Matches</h2>
          <Button variant="ghost" size="sm" asChild>
            <Link to="/candidates">View all →</Link>
          </Button>
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {mockCandidates
            .sort((a, b) => (b.score || 0) - (a.score || 0))
            .slice(0, 3)
            .map((candidate) => (
              <CandidateCard key={candidate.candidateId} candidate={candidate} />
            ))}
        </div>
      </div>

      {/* Recently Shortlisted */}
      <div>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-foreground">Recently Shortlisted</h2>
          <Button variant="ghost" size="sm" asChild>
            <Link to="/candidates?filter=shortlisted">View all →</Link>
          </Button>
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          {mockCandidates
            .filter((c) => c.shortlisted)
            .slice(0, 2)
            .map((candidate) => (
              <CandidateCard key={candidate.candidateId} candidate={candidate} />
            ))}
        </div>
      </div>
    </div>
  );
}
