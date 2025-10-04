from transformers import pipeline

def start_chat_v2():
    """
    Initializes and runs a conversational chatbot.
    This version manually manages the chat history to avoid import issues.
    """
    print("🤖 Initializing chatbot... This may take a moment.")
    chatbot = pipeline("conversational", model="microsoft/DialoGPT-medium")
    print("✅ Chatbot is ready! Type 'exit' to end the conversation.")
    print("-" * 30)

    # We will use simple lists to keep track of the conversation history
    chat_history = {
        "past_user_inputs": [],
        "generated_responses": []
    }

    while True:
        user_input = input(">> You: ")

        if user_input.lower() in ["exit", "quit"]:
            print("👋 Goodbye!")
            break
        
        # Manually build the conversation object the pipeline expects
        conversation = {
            "past_user_inputs": chat_history["past_user_inputs"],
            "generated_responses": chat_history["generated_responses"],
            "text": user_input
        }
        
        # Get the response
        result = chatbot(conversation)

        # Print the latest response from the bot
        bot_response = result["generated_responses"][-1]
        print(f">> Bot: {bot_response}")

        # Update our history with the latest turn
        chat_history["past_user_inputs"].append(user_input)
        chat_history["generated_responses"].append(bot_response)

# --- Start the Chatbot ---
if __name__ == "__main__":
    start_chat_v2()