import { useEffect, useRef, useState } from "react";
import type { ChatMessage } from "../types";
import { fetchChatHistory, streamChat } from "../api/client";
import { ChatIcon, CheckIcon, CopyIcon, PencilIcon, SendIcon } from "./icons";
import MarkdownContent from "./MarkdownContent";

function copyText(message: ChatMessage): string {
  if (message.role === "assistant") {
    return message.content.replace(/\n\n\*Answered (?:from .+|by Gemini)\*$/, "").trim();
  }
  return message.content;
}

export default function ChatTab({ sessionId }: { sessionId: number }) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [streamingText, setStreamingText] = useState("");
  const [error, setError] = useState("");
  const [copiedId, setCopiedId] = useState<number | null>(null);
  const [editingMessageId, setEditingMessageId] = useState<number | null>(null);
  const [editDraft, setEditDraft] = useState("");
  const [editLayout, setEditLayout] = useState<{ minWidth: number; minHeight: number } | null>(
    null,
  );
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const editTextareaRef = useRef<HTMLTextAreaElement>(null);
  const bubbleRefs = useRef<Map<number, HTMLDivElement>>(new Map());
  const MAX_INPUT_LINES = 5;

  const adjustTextareaHeight = (el: HTMLTextAreaElement | null, maxLines = MAX_INPUT_LINES) => {
    if (!el) return;

    el.style.height = "auto";
    const styles = getComputedStyle(el);
    const lineHeight = Number.parseFloat(styles.lineHeight) || 22;
    const paddingTop = Number.parseFloat(styles.paddingTop) || 0;
    const paddingBottom = Number.parseFloat(styles.paddingBottom) || 0;
    const maxHeight = lineHeight * maxLines + paddingTop + paddingBottom;
    const nextHeight = Math.min(el.scrollHeight, maxHeight);

    el.style.height = `${nextHeight}px`;
    el.style.overflowY = el.scrollHeight > maxHeight ? "auto" : "hidden";
  };

  const adjustEditTextareaHeight = (el: HTMLTextAreaElement | null) => {
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${el.scrollHeight}px`;
    el.style.overflowY = "hidden";
  };

  useEffect(() => {
    fetchChatHistory(sessionId).then(setMessages).catch(console.error);
  }, [sessionId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingText, loading, error, editingMessageId]);

  useEffect(() => {
    adjustTextareaHeight(textareaRef.current);
  }, [input]);

  useEffect(() => {
    adjustEditTextareaHeight(editTextareaRef.current);
  }, [editDraft, editingMessageId, editLayout]);

  const setBubbleRef = (messageId: number, el: HTMLDivElement | null) => {
    if (el) bubbleRefs.current.set(messageId, el);
    else bubbleRefs.current.delete(messageId);
  };

  const runChat = async (question: string, editMessageId?: number) => {
    setLoading(true);
    setStreamingText("");
    setError("");

    await streamChat(
      sessionId,
      question,
      (token) => {
        setStreamingText((prev) => prev + token);
      },
      async () => {
        const history = await fetchChatHistory(sessionId);
        setMessages(history);
        setStreamingText("");
        setLoading(false);
      },
      (err) => {
        setError(err.message);
        setStreamingText("");
        setLoading(false);
        fetchChatHistory(sessionId).then(setMessages).catch(console.error);
      },
      editMessageId,
    );
  };

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const question = input.trim();
    setInput("");

    setMessages((prev) => [
      ...prev,
      {
        id: Date.now(),
        role: "user",
        content: question,
        source_label: null,
        created_at: new Date().toISOString(),
      },
    ]);

    await runChat(question);
  };

  const handleCopy = async (message: ChatMessage) => {
    try {
      await navigator.clipboard.writeText(copyText(message));
      setCopiedId(message.id);
      window.setTimeout(() => setCopiedId((current) => (current === message.id ? null : current)), 1500);
    } catch {
      setError("Could not copy to clipboard.");
    }
  };

  const startEdit = (message: ChatMessage) => {
    if (loading) return;
    const bubble = bubbleRefs.current.get(message.id);
    if (bubble) {
      setEditLayout({
        minWidth: bubble.offsetWidth,
        minHeight: bubble.offsetHeight,
      });
    } else {
      setEditLayout(null);
    }
    setEditingMessageId(message.id);
    setEditDraft(message.content);
    setError("");
  };

  const cancelEdit = () => {
    setEditingMessageId(null);
    setEditDraft("");
    setEditLayout(null);
  };

  const handleEditSave = async () => {
    if (!editingMessageId || !editDraft.trim() || loading) return;

    const question = editDraft.trim();
    const messageIndex = messages.findIndex((message) => message.id === editingMessageId);
    if (messageIndex === -1) return;

    setEditingMessageId(null);
    setEditDraft("");
    setEditLayout(null);
    setMessages((prev) => [
      ...prev.slice(0, messageIndex),
      {
        ...prev[messageIndex],
        content: question,
      },
    ]);

    await runChat(question, editingMessageId);
  };

  return (
    <div className="tab-panel chat-panel">
      <div className="chat-info">
        <ChatIcon />
        Answers from your notes first. Falls back to Gemini when not found in source material.
      </div>

      <div className="chat-messages">
        {messages.length === 0 && !loading && !error && (
          <div className="empty-state" style={{ padding: "2rem 1rem", minHeight: "auto" }}>
            <p>Ask anything about this study session...</p>
          </div>
        )}

        {messages.map((message) => (
          <div key={message.id} className={`chat-message-group ${message.role}`}>
            {editingMessageId === message.id ? (
              <>
                <div
                  className={`chat-bubble ${message.role} chat-bubble-editing`}
                  style={
                    editLayout
                      ? {
                          minWidth: editLayout.minWidth,
                          minHeight: editLayout.minHeight,
                        }
                      : undefined
                  }
                >
                  <textarea
                    ref={editTextareaRef}
                    className="chat-edit-textarea"
                    value={editDraft}
                    onChange={(e) => setEditDraft(e.target.value)}
                    autoFocus
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault();
                        handleEditSave();
                      }
                      if (e.key === "Escape") {
                        cancelEdit();
                      }
                    }}
                  />
                </div>
                <div className="chat-edit-actions">
                  <button type="button" className="btn-secondary btn-sm" onClick={cancelEdit}>
                    Cancel
                  </button>
                  <button
                    type="button"
                    className="btn-primary btn-sm"
                    onClick={handleEditSave}
                    disabled={!editDraft.trim()}
                  >
                    Save & send
                  </button>
                </div>
              </>
            ) : (
              <>
                <div
                  ref={(el) => setBubbleRef(message.id, el)}
                  className={`chat-bubble ${message.role}`}
                >
                  <MarkdownContent text={message.content} />
                </div>
                <div className="chat-message-actions">
                  <button
                    type="button"
                    className="chat-action-btn"
                    title={copiedId === message.id ? "Copied" : "Copy"}
                    aria-label={copiedId === message.id ? "Copied" : "Copy message"}
                    onClick={() => handleCopy(message)}
                  >
                    {copiedId === message.id ? <CheckIcon /> : <CopyIcon />}
                  </button>
                  {message.role === "user" && (
                    <button
                      type="button"
                      className="chat-action-btn"
                      title="Edit"
                      aria-label="Edit message"
                      disabled={loading}
                      onClick={() => startEdit(message)}
                    >
                      <PencilIcon />
                    </button>
                  )}
                </div>
              </>
            )}
          </div>
        ))}

        {loading && streamingText && (
          <div className="chat-message-group assistant">
            <div className="chat-bubble assistant">
              <MarkdownContent text={streamingText + "▌"} />
            </div>
          </div>
        )}

        {loading && !streamingText && (
          <div className="chat-message-group assistant">
            <div className="chat-bubble assistant chat-typing">
              <span />
              <span />
              <span />
            </div>
          </div>
        )}

        {error && <p className="error chat-error">{error}</p>}

        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-row">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question about this material..."
          disabled={loading || editingMessageId !== null}
          rows={1}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSend();
            }
          }}
        />
        <button
          className="btn-primary"
          onClick={handleSend}
          disabled={loading || editingMessageId !== null || !input.trim()}
        >
          <SendIcon />
        </button>
      </div>
    </div>
  );
}
