import { useState } from "react";
import type { QuizQuestion, QuizSubmitResponse, SessionDetail } from "../types";
import { fetchSession, generateAdaptiveQuiz, submitQuiz } from "../api/client";
import { getPerformanceBadge } from "../utils/quizBadges";
import { CheckIcon, StarIcon, XIcon } from "./icons";
import QuizMath from "./QuizMath";

function difficultyClass(level: string | null | undefined): string {
  const normalized = (level || "intermediate").toLowerCase();
  if (normalized === "beginner") return "beginner";
  if (normalized === "advanced") return "advanced";
  return "intermediate";
}

function questionDifficultyClass(level: string | undefined): string {
  const normalized = (level || "medium").toLowerCase();
  if (normalized === "easy") return "easy";
  if (normalized === "hard") return "hard";
  return "medium";
}

export default function QuizTab({
  session,
  onSessionUpdated,
}: {
  session: SessionDetail;
  onSessionUpdated?: (session: SessionDetail) => void;
}) {
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [result, setResult] = useState<QuizSubmitResponse | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [generatingPractice, setGeneratingPractice] = useState(false);
  const [practiceError, setPracticeError] = useState("");
  const [practiceNotice, setPracticeNotice] = useState("");

  const quiz = (session.quiz || []).filter(
    (q): q is QuizQuestion => typeof q === "object" && q !== null,
  );

  const refreshSession = async () => {
    const updated = await fetchSession(session.id);
    onSessionUpdated?.(updated);
    return updated;
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    setPracticeError("");
    setPracticeNotice("");
    try {
      const payload: Record<string, string> = {};
      Object.entries(answers).forEach(([key, value]) => {
        payload[key] = value;
      });
      const response = await submitQuiz(session.id, payload, false);
      setResult(response);
    } finally {
      setSubmitting(false);
    }
  };

  const handlePracticeWeakTopics = async () => {
    if (!result?.weak_topics.length) return;

    setGeneratingPractice(true);
    setPracticeError("");
    try {
      const missedQuestions = result.results
        .filter((item) => !item.is_correct)
        .map((item) => item.question);

      await generateAdaptiveQuiz(session.id, result.weak_topics, missedQuestions);
      await refreshSession();
      setResult(null);
      setAnswers({});
      setPracticeNotice("Practice quiz ready — new questions loaded for your weak topics.");
    } catch (error) {
      setPracticeError(
        error instanceof Error ? error.message : "Could not generate practice quiz.",
      );
    } finally {
      setGeneratingPractice(false);
    }
  };

  if (result) {
    const pct = Math.round((result.score / result.total) * 100);
    const hasWeakTopics = result.weak_topics.length > 0;
    const badge = getPerformanceBadge(result.score, result.total);

    return (
      <div className="tab-panel">
        <h3 className="quiz-results-title">Results</h3>

        <div className="quiz-results-summary">
          <div className="quiz-results-left">
            <div className={`quiz-performance-badge ${badge.className}`}>
              <StarIcon />
              <div>
                <span className="quiz-performance-badge-label">{badge.label}</span>
                <p>{badge.description}</p>
              </div>
            </div>
            {session.content_difficulty && (
              <span className={`quiz-difficulty-badge content ${difficultyClass(session.content_difficulty)}`}>
                {session.content_difficulty} content
              </span>
            )}
          </div>

          <div className="quiz-results-right">
            <div className="quiz-score-display">
              <span>{result.score}</span>/{result.total}
              <span className="quiz-score-pct">({pct}%)</span>
            </div>
            {hasWeakTopics && (
              <button
                className="btn-primary btn-sm quiz-weak-practice-btn"
                onClick={handlePracticeWeakTopics}
                disabled={generatingPractice}
              >
                {generatingPractice ? "Generating..." : "Practice Weak Topics"}
              </button>
            )}
          </div>
        </div>

        {hasWeakTopics && (
          <div className="quiz-weak-topics">
            <h4>Areas to work on</h4>
            <div className="quiz-topic-tags">
              {result.weak_topics.map((topic) => (
                <span key={topic} className="quiz-topic-tag">
                  {topic}
                </span>
              ))}
            </div>
            <p className="hint">
              Use Practice Weak Topics to generate new questions focused on these areas.
            </p>
          </div>
        )}

        {result.results.map((item) => (
          <div key={item.question_index} className="quiz-result">
            <div className="quiz-question-meta">
              <h4>Question {item.question_index + 1}</h4>
              {item.topic && <span className="quiz-topic-tag">{item.topic}</span>}
              {item.difficulty && (
                <span className={`quiz-difficulty-badge ${questionDifficultyClass(item.difficulty)}`}>
                  {item.difficulty}
                </span>
              )}
            </div>
            <p className="quiz-math-text">
              <QuizMath text={item.question} />
            </p>
            <p className={`quiz-result-status ${item.is_correct ? "correct" : "incorrect"}`}>
              {item.is_correct ? <CheckIcon /> : <XIcon />}
              {item.is_correct ? "Correct" : "Incorrect"}
            </p>
            {!item.is_correct && (
              <p className="quiz-correct-answer">
                Correct answer:{" "}
                <strong>
                  <QuizMath text={item.correct_answer} />
                </strong>
              </p>
            )}
            <p className="hint quiz-math-text">
              <QuizMath text={item.explanation} />
            </p>
          </div>
        ))}

        {practiceError && <p className="error">{practiceError}</p>}

        <div className="quiz-result-actions">
          <button
            className="btn-secondary"
            onClick={() => {
              setResult(null);
              setAnswers({});
              setPracticeError("");
            }}
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="tab-panel">
      <div className="quiz-header">
        <div>
          <h3>{quiz.length} Questions</h3>
          {session.content_difficulty && (
            <span className={`quiz-difficulty-badge content ${difficultyClass(session.content_difficulty)}`}>
              {session.content_difficulty} level
            </span>
          )}
        </div>
      </div>

      {practiceNotice && (
        <div className="quiz-practice-notice">
          <p>{practiceNotice}</p>
          <button
            type="button"
            className="chat-action-btn"
            aria-label="Dismiss notice"
            onClick={() => setPracticeNotice("")}
          >
            <XIcon />
          </button>
        </div>
      )}

      {quiz.map((question, index) => (
        <div key={index} className="quiz-question">
          <div className="quiz-question-meta">
            <h4>Question {index + 1}</h4>
            {question.topic && <span className="quiz-topic-tag">{question.topic}</span>}
            {question.difficulty && (
              <span className={`quiz-difficulty-badge ${questionDifficultyClass(question.difficulty)}`}>
                {question.difficulty}
              </span>
            )}
          </div>
          <p className="quiz-math-text">
            <QuizMath text={question.question} />
          </p>
          {question.options.map((option) => (
            <label key={option} className="quiz-option">
              <input
                type="radio"
                name={`question-${index}`}
                checked={answers[index] === option}
                onChange={() => setAnswers({ ...answers, [index]: option })}
              />
              <QuizMath text={option} />
            </label>
          ))}
        </div>
      ))}

      <button
        className="btn-primary"
        onClick={handleSubmit}
        disabled={submitting || Object.keys(answers).length < quiz.length}
        style={{ alignSelf: "flex-start" }}
      >
        {submitting ? "Submitting..." : "Submit Quiz"}
      </button>
    </div>
  );
}
