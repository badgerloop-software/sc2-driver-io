import React from "react";
import MessageBlock from "./MessageBlock";

const MessageList = ({ messages }) => {
  return (
    <div className="bg-gray-800 p-4 rounded h-96 overflow-y-auto border border-gray-700">
      {messages.length === 0 ? (
        <p className="text-gray-500">Waiting for messages...</p>
      ) : (
        messages.map((msg, i) => <MessageBlock message={msg} key={i} />)
      )}
    </div>
  );
};

export default MessageList;
