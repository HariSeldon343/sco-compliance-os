// SCO Compliance OS — layout chat: area messaggi scrollabile + input sticky bottom
import { ChatArea } from "@/components/ChatArea";
import { ChatInput } from "@/components/ChatInput";

/**
 * Layout chat principale.
 *
 * Pattern Claude Desktop / OpenHuman:
 *   - ChatArea occupa lo spazio rimanente (flex-1), gestisce internamente il suo scroll.
 *   - ChatInput è sticky in basso (no overflow) e ha bg sco-bg per non vedere
 *     il fondo trasparire mentre si scrolla.
 *
 * Lo sfondo dell'area è sco-bg per coerenza con header e con bg dark mode #0f0f1e.
 */
export function ChatLayout() {
  return (
    <div className="flex h-full flex-col bg-sco-bg">
      <div className="flex-1 overflow-hidden">
        <ChatArea />
      </div>
      <ChatInput />
    </div>
  );
}
