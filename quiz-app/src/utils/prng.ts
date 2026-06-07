// Mulberry32 PRNG
// A simple, fast 32-bit PRNG that can be seeded.
export class PRNG {
  private state: number;

  constructor(seed: number) {
    this.state = seed;
  }

  // Returns a float between 0 (inclusive) and 1 (exclusive)
  public next(): number {
    this.state |= 0;
    this.state = this.state + 0x6D2B79F5 | 0;
    let t = Math.imul(this.state ^ (this.state >>> 15), 1 | this.state);
    t = t + Math.imul(t ^ (t >>> 7), 61 | t) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  }

  // Helper to shuffle an array deterministically
  public shuffleArray<T>(array: T[]): T[] {
    const result = [...array];
    for (let i = result.length - 1; i > 0; i--) {
      const j = Math.floor(this.next() * (i + 1));
      [result[i], result[j]] = [result[j], result[i]];
    }
    return result;
  }

  // Generate a random seed string
  public static generateSeedString(): string {
    return Math.random().toString(36).substring(2, 8).toUpperCase();
  }

  // Simple hash function to convert a string seed to a numeric seed for Mulberry32
  public static hashSeed(seedStr: string): number {
    let hash = 0;
    for (let i = 0; i < seedStr.length; i++) {
      const char = seedStr.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash; // Convert to 32bit integer
    }
    return hash >>> 0; // Ensure unsigned
  }
}
