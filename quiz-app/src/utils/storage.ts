export interface UserStats {
  gamesPlayed: number;
  totalCorrect: number;
  totalQuestions: number;
  highestStreak: number;
  achievements: string[]; // List of unlocked achievement IDs
}

export interface LeaderboardEntry {
  name: string;
  score: number;
  date: string;
}

export const ACHIEVEMENTS = [
  { id: "cold_open", name: "Cold Open", description: "Play your first game", icon: "🎬" },
  { id: "color_calibrated", name: "Color Calibrated", description: "Reach a streak of 5", icon: "🎨" },
  { id: "master_colorist", name: "Master Colorist", description: "Reach a streak of 10", icon: "👑" },
  { id: "cinematographer", name: "The Cinematographer's Eye", description: "Maintain > 80% accuracy in a game", icon: "👁️" },
  { id: "archivist", name: "The Archivist", description: "Play 10 total games", icon: "📚" },
  { id: "one_take_wonder", name: "One-Take Wonder", description: "Finish a game with only one correct question", icon: "1️⃣" },
  { id: "action", name: "Action!", description: "Answer your very first question correctly", icon: "💥" },
  { id: "cutting_room", name: "Cutting Room Floor", description: "Lose your first heart", icon: "✂️" },
  { id: "thats_a_wrap", name: "That's a Wrap", description: "Complete your first full quiz session", icon: "🎬" },
  { id: "reverse_shot", name: "Reverse Shot", description: "Correctly answer one 'Which film is this?' and one 'Which barcode is this?' question", icon: "🔄" },
  { id: "cliffhanger", name: "Cliffhanger", description: "Answer 2 questions correctly with one heart remaining", icon: "🧗" },
  { id: "quick_cut", name: "Quick Cut", description: "Answer 3 questions correctly in under 5 seconds each", icon: "⏱️" },
  { id: "plot_twist", name: "Plot Twist", description: "Build a streak of 5 correct answers immediately after losing a heart", icon: "🌪️" },
  { id: "fast_forward", name: "Fast Forward", description: "Complete an entire quiz session in under 60 seconds", icon: "⏩" },
  { id: "directors_cut", name: "The Director's Cut", description: "Share a link", icon: "📣" }
];

const STATS_KEY = 'cinecode_user_stats';
const LEADERBOARD_KEY = 'cinecode_leaderboard';

export const Storage = {
  getStats: (): UserStats => {
    const defaultStats: UserStats = {
      gamesPlayed: 0,
      totalCorrect: 0,
      totalQuestions: 0,
      highestStreak: 0,
      achievements: []
    };
    try {
      const data = localStorage.getItem(STATS_KEY);
      return data ? { ...defaultStats, ...JSON.parse(data) } : defaultStats;
    } catch (e) {
      return defaultStats;
    }
  },

  saveStats: (stats: UserStats) => {
    localStorage.setItem(STATS_KEY, JSON.stringify(stats));
  },

  unlockAchievement: (id: string): boolean => {
    const stats = Storage.getStats();
    if (!stats.achievements.includes(id)) {
      stats.achievements.push(id);
      Storage.saveStats(stats);
      return true; // Newly unlocked
    }
    return false; // Already unlocked
  },

  getLeaderboard: (): LeaderboardEntry[] => {
    try {
      const data = localStorage.getItem(LEADERBOARD_KEY);
      return data ? JSON.parse(data) : [];
    } catch (e) {
      return [];
    }
  },

  saveScore: (score: number, name: string = "Player") => {
    const lb = Storage.getLeaderboard();
    lb.push({ name, score, date: new Date().toISOString() });
    // Sort descending
    lb.sort((a, b) => b.score - a.score);
    // Keep top 5
    const top5 = lb.slice(0, 5);
    localStorage.setItem(LEADERBOARD_KEY, JSON.stringify(top5));
    return top5;
  }
};
