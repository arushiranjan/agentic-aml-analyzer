import { motion } from "framer-motion";
import { ArrowRight, CheckCircle2 } from "lucide-react";
import type { PlanStep } from "@/types";
import { Badge } from "@/components/ui/badge";

export function PlanSteps({ steps, source }: { steps: PlanStep[]; source: "llm" | "fallback" }) {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <Badge variant={source === "llm" ? "primary" : "outline"}>
          {source === "llm" ? "LLM Planner" : "Keyword Fallback Planner"}
        </Badge>
      </div>
      <ol className="space-y-2">
        {steps.map((step, i) => (
          <motion.li
            key={`${step.tool}-${i}`}
            initial={{ opacity: 0, x: -6 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.05, duration: 0.2 }}
            className="flex items-start gap-3 rounded-md border border-border bg-muted/40 px-3 py-2"
          >
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
            <div className="flex flex-1 flex-wrap items-center gap-2 text-sm">
              <span className="font-mono font-medium text-foreground">{step.tool}</span>
              {i < steps.length - 1 && <ArrowRight className="h-3 w-3 text-muted-foreground" />}
              <span className="text-muted-foreground">{step.why}</span>
            </div>
          </motion.li>
        ))}
      </ol>
    </div>
  );
}
