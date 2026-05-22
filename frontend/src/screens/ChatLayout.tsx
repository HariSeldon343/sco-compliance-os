// SCO Compliance OS — layout chat: area messaggi + input bottom
import { ChatArea } from "@/components/ChatArea";
import { ChatInput } from "@/components/ChatInput";

export function ChatLayout() {
  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 overflow-hidden">
        <ChatArea />
      </div>
      <ChatInput />
    </div>
  );
}
