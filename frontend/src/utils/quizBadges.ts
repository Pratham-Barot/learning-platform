export interface PerformanceBadge {
  id: string;
  label: string;
  description: string;
  className: string;
}

export function getPerformanceBadge(score: number, total: number): PerformanceBadge {
  if (total <= 0) {
    return {
      id: "starter",
      label: "Starter",
      description: "Complete a quiz to earn your first badge.",
      className: "starter",
    };
  }

  const pct = Math.round((score / total) * 100);

  if (pct === 100) {
    return {
      id: "perfect",
      label: "Perfect Master",
      description: "Flawless score — you nailed every question.",
      className: "perfect",
    };
  }
  if (pct >= 80) {
    return {
      id: "expert",
      label: "Expert",
      description: "Strong mastery — you clearly understand this material.",
      className: "expert",
    };
  }
  if (pct >= 60) {
    return {
      id: "proficient",
      label: "Proficient",
      description: "Solid grasp — a little more practice will sharpen your skills.",
      className: "proficient",
    };
  }
  if (pct >= 40) {
    return {
      id: "learner",
      label: "Learner",
      description: "Good effort — review explanations and try weak-topic practice.",
      className: "learner",
    };
  }

  return {
    id: "explorer",
    label: "Explorer",
    description: "Keep going — focus on weak topics to build your foundation.",
    className: "explorer",
  };
}
