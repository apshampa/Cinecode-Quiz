import { useState, useEffect, useCallback, useRef } from 'react';
import { Play, RotateCcw, AlertTriangle, ExternalLink, Trophy, Flame, Heart, CheckCircle2, XCircle, SkipForward } from 'lucide-react';

interface MovieRecord {
  title: string;
  filename: string;
  colors: string[];
  duration_seconds: number;
}

const SAMPLE_DATA: MovieRecord[] = [
  {
    title: "The Matrix (1999)",
    filename: "sample-matrix.png",
    colors: ["#051508", "#0C3013", "#124B1D", "#1C7A2E", "#22C55E"],
    duration_seconds: 8160
  },
  {
    title: "Inception (2010)",
    filename: "sample-inception.png",
    colors: ["#070F1A", "#14253B", "#2B4763", "#5C7E9E", "#A0B9D1"],
    duration_seconds: 8880
  },
  {
    title: "Mad Max: Fury Road (2015)",
    filename: "sample-madmax.png",
    colors: ["#78350F", "#B45309", "#D97706", "#2563EB", "#1D4ED8"],
    duration_seconds: 7200
  },
  {
    title: "Interstellar (2014)",
    filename: "sample-interstellar.png",
    colors: ["#020617", "#0F172A", "#334155", "#64748B", "#CBD5E1"],
    duration_seconds: 10140
  },
  {
    title: "Amélie (2001)",
    filename: "sample-amelie.png",
    colors: ["#064E3B", "#047857", "#B91C1C", "#F59E0B", "#FCD34D"],
    duration_seconds: 7320
  },
  {
    title: "La La Land (2016)",
    filename: "sample-lalaland.png",
    colors: ["#172554", "#1E1B4B", "#581C87", "#DB2777", "#FBBF24"],
    duration_seconds: 7680
  },
  {
    title: "Blade Runner 2049 (2017)",
    filename: "sample-bladerunner.png",
    colors: ["#0F172A", "#EA580C", "#CA8A04", "#06B6D4", "#0891B2"],
    duration_seconds: 9840
  },
  {
    title: "Spider-Man: Into the Spider-Verse (2018)",
    filename: "sample-spiderverse.png",
    colors: ["#1E1B4B", "#311042", "#701A75", "#DB2777", "#2563EB"],
    duration_seconds: 7020
  }
];

function App() {
  const [gameState, setGameState] = useState<'menu' | 'playing' | 'gameover'>('menu');
  const [quizData, setQuizData] = useState<MovieRecord[]>([]);
  const [isSampleMode, setIsSampleMode] = useState(false);
  const [, setDbError] = useState<string | null>(null);

  // Gameplay States
  const [score, setScore] = useState(0);
  const [streak, setStreak] = useState(0);
  const [highScore, setHighScore] = useState(0);
  const [lives, setLives] = useState(3);
  const [questionType, setQuestionType] = useState<'guess-movie' | 'guess-barcode'>('guess-movie');

  const [correctMovie, setCorrectMovie] = useState<MovieRecord | null>(null);
  const [options, setOptions] = useState<MovieRecord[]>([]);
  const [selectedIdx, setSelectedIdx] = useState<number | null>(null);
  const [isAnswered, setIsAnswered] = useState(false);
  const [feedback, setFeedback] = useState<{ isCorrect: boolean; text: string } | null>(null);
  const [shakeCard, setShakeCard] = useState(false);

  // Loading States for Images
  const [isMainImageLoading, setIsMainImageLoading] = useState(true);
  const [loadedGridImages, setLoadedGridImages] = useState<Record<string, boolean>>({});

  const imageErrorsRef = useRef<Record<string, boolean>>({});

  // Load High Score and Quiz Database
  useEffect(() => {
    const savedHighScore = localStorage.getItem('cinecode_quiz_highscore');
    if (savedHighScore) {
      setHighScore(parseInt(savedHighScore, 10));
    }

    // Try fetching the generated database
    fetch(`${import.meta.env.BASE_URL}quiz/quiz_data.json`)
      .then((res) => {
        if (!res.ok) throw new Error("Could not load database file");
        return res.json();
      })
      .then((data: MovieRecord[]) => {
        if (data && data.length >= 4) {
          setQuizData(data);
          setIsSampleMode(false);
        } else {
          throw new Error("Database needs at least 4 movies to play the quiz.");
        }
      })
      .catch((err) => {
        setDbError(err.message || "Failed to load database. Playing in Sample Mode.");
        setQuizData(SAMPLE_DATA);
        setIsSampleMode(true);
      });
  }, []);

  const shuffleArray = <T,>(arr: T[]): T[] => {
    return [...arr].sort(() => Math.random() - 0.5);
  };

  const getFormatDuration = (seconds: number) => {
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    return hrs > 0 ? `${hrs}h ${mins}m` : `${mins}m`;
  };

  // Generate a new question
  const nextQuestion = useCallback(() => {
    if (quizData.length < 4) return;

    setIsAnswered(false);
    setSelectedIdx(null);
    setFeedback(null);
    setShakeCard(false);

    // Reset image loading states
    setIsMainImageLoading(true);
    setLoadedGridImages({});

    // Randomize Question Type
    const type = Math.random() > 0.5 ? 'guess-movie' : 'guess-barcode';
    setQuestionType(type);

    // Choose Correct Movie
    const target = quizData[Math.floor(Math.random() * quizData.length)];
    setCorrectMovie(target);

    // Select Distractors
    const others = quizData.filter(m => m.title !== target.title);
    const shuffledOthers = shuffleArray(others);
    const distractors = shuffledOthers.slice(0, 3);

    // Combine and shuffle
    const combined = shuffleArray([target, ...distractors]);
    setOptions(combined);
  }, [quizData]);

  const startNewGame = () => {
    setScore(0);
    setStreak(0);
    setLives(3);
    setGameState('playing');
    imageErrorsRef.current = {};
    setTimeout(() => nextQuestion(), 50);
  };

  const handleSelectOption = (idx: number, movieOption: MovieRecord) => {
    if (isAnswered || !correctMovie) return;

    setSelectedIdx(idx);
    setIsAnswered(true);

    const isCorrect = movieOption.title === correctMovie.title;

    if (isCorrect) {
      const newScore = score + 10 + (streak * 2);
      const newStreak = streak + 1;
      setScore(newScore);
      setStreak(newStreak);
      setFeedback({ isCorrect: true, text: `Correct! ${getFormatDuration(correctMovie.duration_seconds)} duration.` });

      if (newScore > highScore) {
        setHighScore(newScore);
        localStorage.setItem('cinecode_quiz_highscore', newScore.toString());
      }
    } else {
      setStreak(0);
      setShakeCard(true);
      const newLives = lives - 1;
      setLives(newLives);
      setFeedback({ isCorrect: false, text: `Incorrect! It was '${correctMovie.title}'.` });

      if (newLives <= 0) {
        setTimeout(() => {
          setGameState('gameover');
        }, 1500);
      }
    }
  };

  // Skip the current question without affecting hearts (resets streak)
  const handleSkipQuestion = () => {
    if (isAnswered) return;
    setStreak(0); // Reset streak for fairness, but keep lives and score
    nextQuestion();
  };

  // Check if an image failed to load, to fall back to color gradient
  const handleImageError = (filename: string) => {
    imageErrorsRef.current[filename] = true;
    setQuizData(prev => [...prev]);
  };

  // Generate CSS background gradient from palette
  const getGradientFromPalette = (colors: string[]) => {
    if (!colors || colors.length === 0) return 'linear-gradient(90deg, #1e293b, #0f172a)';
    if (colors.length === 1) return colors[0];
    return `linear-gradient(90deg, ${colors.join(', ')})`;
  };

  return (
    <div className="app-container">
      {/* HEADER SECTION */}
      <header style={{ width: '100%', textAlign: 'center', marginBottom: '2rem' }}>
        <h1>CineCode <span className="gradient-title">Quiz</span></h1>
        <p style={{ color: 'var(--text-muted)', fontSize: '1rem', marginTop: '0.2rem' }}>
          Test your movie knowledge by decoding cinematography color timelines
        </p>
      </header>

      {/* GAME MENU */}
      {gameState === 'menu' && (
        <main className="glass-panel menu-container" style={{ animation: 'slide-up 0.4s ease' }}>
          <div className="badge-highlight">
            <Trophy size={14} style={{ display: 'inline', marginRight: '4px', verticalAlign: 'middle' }} />
            High Score: {highScore} pts
          </div>

          <h2 style={{ fontSize: '1.8rem', fontWeight: 700, marginBottom: '1rem' }}>Ready to decode?</h2>
          <p style={{ color: 'var(--text-muted)', maxWidth: '500px', marginBottom: '2rem', lineHeight: '1.6' }}>
            A CineCode is a visualization of a movie's color.
            We will show you a cinecode and you guess the film, or vice-versa.
          </p>

          {/* Database Alert status */}
          {isSampleMode ? (
            <div className="setup-warning">
              <div className="setup-title">
                <AlertTriangle size={18} /> Playing in Sample Mode
              </div>
              <p>
                We couldn't detect your local movie database index at <span style={{ color: '#fb7185' }}>public/quiz/quiz_data.json</span>.
                To load your own films, run the Generator GUI on your movies folder and copy files to the quiz folder:
              </p>
              <code className="setup-code">
                C:\Users\revan\Downloads\cinecode\quiz-app\public\quiz\
              </code>
            </div>
          ) : (
            <div style={{
              background: 'rgba(16, 185, 129, 0.05)',
              border: '1px solid rgba(16, 185, 129, 0.2)',
              borderRadius: 'var(--radius)',
              padding: '12px 20px',
              marginBottom: '2rem',
              color: 'var(--success)',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              fontSize: '0.95rem'
            }}>
              <CheckCircle2 size={18} /> Currently a Database with {quizData.length} movies!
            </div>
          )}

          <div className="play-buttons">
            <button className="btn btn-primary" onClick={startNewGame}>
              <Play size={18} /> Start Quiz Game
            </button>
          </div>
        </main>
      )}

      {/* GAMEPLAY VIEW */}
      {gameState === 'playing' && correctMovie && (
        <main className={`glass-panel ${shakeCard ? 'shake' : ''}`} style={{ padding: '2rem' }}>

          {/* Progress Header */}
          <div className="game-header">
            <div className="stat-box" style={{ color: 'var(--primary)' }}>
              <span>Score: {score}</span>
            </div>

            <div className="stat-box" style={{ color: '#f59e0b', visibility: streak > 0 ? 'visible' : 'hidden' }}>
              <Flame size={20} fill="#f59e0b" />
              <span>{streak} Streak</span>
            </div>

            <div className="hearts-container">
              {[1, 2, 3].map((heartNum) => (
                <Heart
                  key={heartNum}
                  className={`heart-svg ${heartNum > lives ? 'heart-empty' : ''} ${heartNum === lives + 1 && isAnswered && !feedback?.isCorrect ? 'heart-lost' : ''}`}
                />
              ))}
            </div>
          </div>

          {/* QUESTION TYPE: GUESS MOVIE FROM BARCODE */}
          {questionType === 'guess-movie' && (
            <div className="question-container">
              <h3 style={{ fontSize: '1.25rem', marginBottom: '1.25rem', textAlign: 'center' }}>
                Which movie does this color cinecode belong to?
              </h3>

              <div
                className="barcode-wrapper"
                style={{
                  borderColor: isAnswered ? (feedback?.isCorrect ? 'var(--success)' : 'var(--error)') : 'var(--border)',
                  boxShadow: isAnswered ? (feedback?.isCorrect ? '0 0 25px var(--success-glow)' : '0 0 25px var(--error-glow)') : 'var(--shadow)'
                }}
              >
                {/* Shimmer loading skeleton state */}
                {!imageErrorsRef.current[correctMovie.filename] && !isSampleMode && isMainImageLoading && (
                  <div className="skeleton-loader">
                    <span className="skeleton-text">Loading CineCode...</span>
                  </div>
                )}

                {imageErrorsRef.current[correctMovie.filename] || isSampleMode ? (
                  <div style={{
                    width: '100%',
                    height: '100%',
                    background: getGradientFromPalette(correctMovie.colors),
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    padding: '20px',
                    textAlign: 'center'
                  }}>
                    <span style={{ fontSize: '0.85rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
                      CineCode Spectrum Palette
                    </span>
                  </div>
                ) : (
                  <img
                    src={`${import.meta.env.BASE_URL}quiz/${correctMovie.filename}`}
                    className="barcode-image"
                    style={{ opacity: isMainImageLoading ? 0 : 1 }}
                    alt="Movie Barcode"
                    onLoad={() => setIsMainImageLoading(false)}
                    onError={() => handleImageError(correctMovie.filename)}
                  />
                )}
              </div>

              {/* Multiple Choice Options */}
              <div className="options-grid">
                {options.map((option, idx) => {
                  let btnClass = "";
                  if (isAnswered) {
                    if (option.title === correctMovie.title) {
                      btnClass = "correct";
                    } else if (selectedIdx === idx) {
                      btnClass = "incorrect";
                    } else {
                      btnClass = "dimmed";
                    }
                  }

                  return (
                    <button
                      key={idx}
                      className={`option-btn ${btnClass}`}
                      disabled={isAnswered}
                      onClick={() => handleSelectOption(idx, option)}
                    >
                      <span>{option.title}</span>
                      {isAnswered && option.title === correctMovie.title && <CheckCircle2 size={18} />}
                      {isAnswered && selectedIdx === idx && option.title !== correctMovie.title && <XCircle size={18} />}
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* QUESTION TYPE: GUESS BARCODE FROM MOVIE */}
          {questionType === 'guess-barcode' && (
            <div className="question-container">
              <h3 style={{ fontSize: '1.25rem', marginBottom: '0.5rem', textAlign: 'center' }}>
                Which spectrum represents:
              </h3>
              <h2 style={{ fontSize: '1.8rem', fontWeight: 800, color: 'var(--primary)', marginBottom: '1.5rem', textAlign: 'center' }}>
                {correctMovie.title}
              </h2>

              {/* Barcode options grid */}
              <div className="barcodes-grid">
                {options.map((option, idx) => {
                  let cardClass = "";
                  if (isAnswered) {
                    if (option.title === correctMovie.title) {
                      cardClass = "correct";
                    } else if (selectedIdx === idx) {
                      cardClass = "incorrect";
                    } else {
                      cardClass = "dimmed";
                    }
                  }

                  const isGridImgLoaded = loadedGridImages[option.filename] || false;

                  return (
                    <div
                      key={idx}
                      className={`barcode-option-card ${cardClass} ${isAnswered ? 'disabled' : ''}`}
                      onClick={() => !isAnswered && handleSelectOption(idx, option)}
                    >
                      {/* Grid Shimmer skeleton loaders */}
                      {!imageErrorsRef.current[option.filename] && !isSampleMode && !isGridImgLoaded && (
                        <div className="skeleton-loader" />
                      )}

                      {imageErrorsRef.current[option.filename] || isSampleMode ? (
                        <div style={{
                          width: '100%',
                          height: '100%',
                          background: getGradientFromPalette(option.colors),
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center'
                        }} />
                      ) : (
                        <img
                          src={`${import.meta.env.BASE_URL}quiz/${option.filename}`}
                          className="barcode-image"
                          style={{ opacity: isGridImgLoaded ? 1 : 0 }}
                          alt="Barcode option"
                          onLoad={() => setLoadedGridImages(prev => ({ ...prev, [option.filename]: true }))}
                          onError={() => handleImageError(option.filename)}
                        />
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Correct feedback: Dominant color swatches reveal */}
          {isAnswered && feedback && (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: '100%', marginTop: '1rem', animation: 'slide-up 0.25s ease' }}>
              <div className={`feedback-msg ${feedback.isCorrect ? 'correct' : 'incorrect'}`}>
                {feedback.isCorrect ? <CheckCircle2 size={20} /> : <XCircle size={20} />}
                {feedback.text}
              </div>

              {/* Swatch display */}
              <div style={{ width: '100%', maxWidth: '400px' }}>
                <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)', display: 'block', textAlign: 'center', marginBottom: '4px' }}>
                  Dominant Color Palette
                </span>
                <div className="color-palette-reveal">
                  {correctMovie.colors.map((color, idx) => (
                    <div
                      key={idx}
                      className="color-swatch"
                      style={{ backgroundColor: color }}
                      title={color}
                    />
                  ))}
                </div>
              </div>

              {/* Next Question Trigger */}
              {lives > 0 && (
                <button
                  className="btn btn-primary"
                  onClick={nextQuestion}
                  style={{ marginTop: '2rem', padding: '12px 35px' }}
                >
                  Next Movie &rarr;
                </button>
              )}
            </div>
          )}

          {/* Bottom Game Controls: Back to Menu & Skip Question */}
          {!isAnswered && (
            <div className="game-controls">
              <button className="btn btn-secondary" onClick={() => setGameState('menu')}>
                Back to Menu
              </button>
              <button className="btn btn-outline-primary" onClick={handleSkipQuestion}>
                <SkipForward size={16} /> Skip Question
              </button>
            </div>
          )}

        </main>
      )}

      {/* GAME OVER SCREEN */}
      {gameState === 'gameover' && (
        <main className="glass-panel gameover-container" style={{ animation: 'slide-up 0.4s ease' }}>
          <div className="badge-highlight">Game Over</div>

          <h2 style={{ fontSize: '2.5rem', fontWeight: 800 }}>Finished!</h2>
          <div className="final-score">{score}</div>
          <p style={{ color: 'var(--text-muted)', fontSize: '1.1rem' }}>points earned</p>

          <div className="gameover-stats">
            <div className="summary-stat">
              <span className="stat-val" style={{ color: '#f59e0b' }}>{highScore}</span>
              <span className="stat-lbl">High Score</span>
            </div>
            <div className="summary-stat">
              <span className="stat-val" style={{ color: 'var(--success)' }}>
                {Math.round((score / 10) * 100) / 10}%
              </span>
              <span className="stat-lbl">Accuracy</span>
            </div>
          </div>

          <p style={{ color: 'var(--text-muted)', maxWidth: '350px', marginBottom: '2rem', fontSize: '0.95rem' }}>
            {score >= highScore && score > 0
              ? "👑 SPECTACULAR! You set a new personal record! You truly are a cinematic connoisseur."
              : score >= 50
                ? "Good job! You have a solid eye for movie color aesthetics."
                : "Keep studying those color palettes and try again!"}
          </p>

          <div style={{ display: 'flex', gap: '1rem', width: '100%', maxWidth: '350px', justifyContent: 'center' }}>
            <button className="btn btn-primary" onClick={startNewGame} style={{ flex: 1 }}>
              <RotateCcw size={16} /> Play Again
            </button>
            <button className="btn btn-secondary" onClick={() => setGameState('menu')} style={{ flex: 1 }}>
              Main Menu
            </button>
          </div>
        </main>
      )}

      {/* FOOTER LINK: UPDATED REDIRECT URL */}
      <a
        href="https://cinecode.revanth.design/"
        target="_blank"
        rel="noopener noreferrer"
        className="footer-link"
      >
        <span>Generate your own Cinecodes here!</span>
        <ExternalLink size={14} />
      </a>
    </div>
  );
}

export default App;
