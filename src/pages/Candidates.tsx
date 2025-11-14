import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Search, SlidersHorizontal } from "lucide-react";
import CandidateCard from "@/components/candidate/CandidateCard";
import { mockCandidates } from "@/lib/mockData";
import { useToast } from "@/hooks/use-toast";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { Label } from "@/components/ui/label";

export default function Candidates() {
  const { toast } = useToast();
  const [searchQuery, setSearchQuery] = useState("");
  const [showFilters, setShowFilters] = useState(false);
  const [experienceRange, setExperienceRange] = useState([0, 10]);
  const [sortBy, setSortBy] = useState("score");
  const [candidates, setCandidates] = useState(mockCandidates);

  const handleShortlist = (candidateId: string) => {
    setCandidates((prev) =>
      prev.map((c) =>
        c.candidateId === candidateId ? { ...c, shortlisted: !c.shortlisted } : c
      )
    );
    toast({
      title: "Candidate updated",
      description: "Shortlist status has been updated.",
    });
  };

  const filteredCandidates = candidates
    .filter((c) => {
      if (!searchQuery) return true;
      const query = searchQuery.toLowerCase();
      return (
        c.name.toLowerCase().includes(query) ||
        c.title.toLowerCase().includes(query) ||
        c.skills.some((s) => s.toLowerCase().includes(query)) ||
        c.currentCompany.toLowerCase().includes(query)
      );
    })
    .filter((c) => c.experienceYears >= experienceRange[0] && c.experienceYears <= experienceRange[1])
    .sort((a, b) => {
      if (sortBy === "score") return (b.score || 0) - (a.score || 0);
      if (sortBy === "experience") return b.experienceYears - a.experienceYears;
      if (sortBy === "name") return a.name.localeCompare(b.name);
      return 0;
    });

  return (
    <div className="min-h-screen p-6 lg:p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="mb-2 text-3xl font-bold text-foreground">Candidates</h1>
        <p className="text-muted-foreground">
          Search and filter through {candidates.length} candidates
        </p>
      </div>

      {/* Search & Filters */}
      <Card className="mb-6 p-6">
        <div className="mb-4 flex flex-col gap-4 sm:flex-row">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search by name, skills, company, or use natural language..."
              className="pl-10"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <Button
            variant="outline"
            onClick={() => setShowFilters(!showFilters)}
            className="sm:w-auto"
          >
            <SlidersHorizontal className="mr-2 h-4 w-4" />
            Filters
          </Button>
        </div>

        {/* Advanced filters */}
        {showFilters && (
          <div className="grid gap-6 border-t border-border pt-6 md:grid-cols-2 lg:grid-cols-3">
            <div className="space-y-3">
              <Label>Sort By</Label>
              <Select value={sortBy} onValueChange={setSortBy}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="score">Match Score</SelectItem>
                  <SelectItem value="experience">Experience</SelectItem>
                  <SelectItem value="name">Name</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-3">
              <Label>
                Experience: {experienceRange[0]} - {experienceRange[1]} years
              </Label>
              <Slider
                value={experienceRange}
                onValueChange={setExperienceRange}
                min={0}
                max={15}
                step={1}
                className="pt-2"
              />
            </div>

            <div className="flex items-end">
              <Button
                variant="outline"
                onClick={() => {
                  setSearchQuery("");
                  setExperienceRange([0, 10]);
                  setSortBy("score");
                }}
              >
                Reset Filters
              </Button>
            </div>
          </div>
        )}
      </Card>

      {/* Results count */}
      <div className="mb-4 text-sm text-muted-foreground">
        Showing {filteredCandidates.length} of {candidates.length} candidates
      </div>

      {/* Candidates grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {filteredCandidates.map((candidate) => (
          <CandidateCard
            key={candidate.candidateId}
            candidate={candidate}
            onShortlist={handleShortlist}
          />
        ))}
      </div>

      {filteredCandidates.length === 0 && (
        <Card className="p-12 text-center">
          <p className="text-muted-foreground">
            No candidates found matching your criteria. Try adjusting your filters.
          </p>
        </Card>
      )}
    </div>
  );
}
