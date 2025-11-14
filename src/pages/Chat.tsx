import { useState, useRef, useEffect } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Send, Bot, User, Sparkles, ExternalLink, ArrowLeft } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { mockCandidates } from "@/lib/mockData";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  citations?: {
    candidateId: string;
    candidateName: string;
    snippet: string;
  }[];
}

export default function Chat() {
  const navigate = useNavigate();
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      role: "assistant",
      content:
        "Hello! I'm your AI recruitment assistant. I can help you find the perfect candidates, answer questions about their experience, and provide intelligent recommendations. What would you like to know?",
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    // Simulate AI response
    setTimeout(() => {
      const responses = [
        {
          content:
            "Based on your query, I found 3 excellent candidates with strong Kubernetes and backend experience. Asha Kumar stands out with 99.9% uptime achievement in microservices deployment.",
          citations: [
            {
              candidateId: mockCandidates[0].candidateId,
              candidateName: mockCandidates[0].name,
              snippet:
                "Designed microservices architecture deployed on Kubernetes with 99.9% uptime",
            },
          ],
        },
        {
          content:
            "I recommend focusing on candidates with 5+ years of experience in cloud-native technologies. Priya Patel has excellent DevOps credentials with infrastructure automation expertise.",
          citations: [
            {
              candidateId: mockCandidates[2].candidateId,
              candidateName: mockCandidates[2].name,
              snippet:
                "Automated infrastructure provisioning using Terraform and reduced deployment time by 70%",
            },
          ],
        },
        {
          content:
            "All three candidates match your criteria well. Would you like me to compare their specific skills, or help you draft interview questions tailored to their experience?",
          citations: [],
        },
      ];

      const response = responses[Math.floor(Math.random() * responses.length)];

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: response.content,
        timestamp: new Date(),
        citations: response.citations.length > 0 ? response.citations : undefined,
      };

      setMessages((prev) => [...prev, assistantMessage]);
      setIsLoading(false);
    }, 1500);
  };

  const suggestedQueries = [
    "Find senior backend engineers with Kubernetes",
    "Show candidates with Python and cloud experience",
    "Who has the most experience with microservices?",
    "Compare top 3 candidates",
  ];

  return (
    <div className="flex h-screen flex-col lg:flex-row">
      {/* Main chat area */}
      <div className="flex flex-1 flex-col">
        {/* Header */}
        <div className="border-b border-border bg-card p-6">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-gradient-to-br from-primary to-secondary">
                <Bot className="h-6 w-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-foreground">AI Recruitment Assistant</h1>
                <p className="text-sm text-muted-foreground">
                  Powered by RAG & Natural Language Search
                </p>
              </div>
            </div>
            <Button variant="ghost" onClick={() => navigate(-1)} className="gap-2 text-sm">
              <ArrowLeft className="h-4 w-4" />
              Back
            </Button>
          </div>
        </div>

        {/* Messages */}
        <ScrollArea className="flex-1 p-6">
          <div className="mx-auto max-w-3xl space-y-6">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex gap-3 ${message.role === "user" ? "flex-row-reverse" : ""}`}
              >
                <div
                  className={`flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full ${
                    message.role === "user"
                      ? "bg-primary"
                      : "bg-gradient-to-br from-secondary to-primary"
                  }`}
                >
                  {message.role === "user" ? (
                    <User className="h-4 w-4 text-white" />
                  ) : (
                    <Bot className="h-4 w-4 text-white" />
                  )}
                </div>
                <div className="flex-1 space-y-2">
                  <Card
                    className={`p-4 ${
                      message.role === "user"
                        ? "bg-primary text-primary-foreground ml-12"
                        : "bg-card mr-12"
                    }`}
                  >
                    <p className="text-sm">{message.content}</p>
                  </Card>

                  {/* Citations */}
                  {message.citations && message.citations.length > 0 && (
                    <div className="mr-12 space-y-2">
                      <p className="text-xs font-medium text-muted-foreground">
                        Referenced candidates:
                      </p>
                      {message.citations.map((citation, idx) => (
                        <Card key={idx} className="border-primary/20 p-3">
                          <div className="mb-2 flex items-start justify-between gap-2">
                            <p className="text-sm font-medium text-foreground">
                              {citation.candidateName}
                            </p>
                            <Button variant="ghost" size="sm" asChild>
                              <Link to={`/candidate/${citation.candidateId}`}>
                                <ExternalLink className="h-3 w-3" />
                              </Link>
                            </Button>
                          </div>
                          <p className="text-xs text-muted-foreground">"{citation.snippet}"</p>
                        </Card>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}

            {isLoading && (
              <div className="flex gap-3">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-secondary to-primary">
                  <Bot className="h-4 w-4 text-white" />
                </div>
                <Card className="mr-12 p-4">
                  <div className="flex items-center gap-2">
                    <Sparkles className="h-4 w-4 animate-pulse text-primary" />
                    <span className="text-sm text-muted-foreground">Thinking...</span>
                  </div>
                </Card>
              </div>
            )}
            <div ref={scrollRef} />
          </div>
        </ScrollArea>

        {/* Input */}
        <div className="border-t border-border bg-card p-6">
          <div className="mx-auto max-w-3xl">
            {messages.length === 1 && (
              <div className="mb-4">
                <p className="mb-2 text-sm text-muted-foreground">Try asking:</p>
                <div className="flex flex-wrap gap-2">
                  {suggestedQueries.map((query, idx) => (
                    <Badge
                      key={idx}
                      variant="outline"
                      className="cursor-pointer hover:bg-accent"
                      onClick={() => setInput(query)}
                    >
                      {query}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
            <div className="flex gap-2">
              <Input
                placeholder="Ask me anything about candidates..."
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSend()}
                disabled={isLoading}
              />
              <Button onClick={handleSend} disabled={isLoading || !input.trim()}>
                <Send className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Sidebar - Context */}
      <aside className="hidden w-80 border-l border-border bg-card p-6 lg:block">
        <h2 className="mb-4 text-sm font-semibold text-foreground">Context & Tips</h2>
        <div className="space-y-4">
          <Card className="p-4">
            <h3 className="mb-2 text-sm font-medium text-foreground">What I can do</h3>
            <ul className="space-y-1 text-xs text-muted-foreground">
              <li>• Search candidates using natural language</li>
              <li>• Compare candidate qualifications</li>
              <li>• Suggest best matches for roles</li>
              <li>• Generate interview questions</li>
              <li>• Provide candidate insights</li>
            </ul>
          </Card>

          <Card className="border-secondary/20 bg-secondary/5 p-4">
            <h3 className="mb-2 text-sm font-medium text-foreground">Pro tip</h3>
            <p className="text-xs text-muted-foreground">
              Be specific about skills, experience level, and requirements for best results.
            </p>
          </Card>

          <Card className="p-4">
            <h3 className="mb-2 text-sm font-medium text-foreground">Current database</h3>
            <div className="text-xs text-muted-foreground">
              <p className="mb-1">
                <strong className="text-foreground">{mockCandidates.length}</strong> candidates
                indexed
              </p>
              <p>Last updated: Today</p>
            </div>
          </Card>
        </div>
      </aside>
    </div>
  );
}
