import { motion } from "framer-motion";
import { ShieldCheck } from "lucide-react";

export function LoadingScreen({ label = "Loading Sentinel AML..." }: { label?: string }) {
  return (
    <div className="flex h-screen w-full flex-col items-center justify-center gap-4 bg-background">
      <motion.div
        animate={{ opacity: [0.4, 1, 0.4] }}
        transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }}
      >
        <ShieldCheck className="h-10 w-10 text-primary" />
      </motion.div>
      <p className="text-sm text-muted-foreground">{label}</p>
    </div>
  );
}
