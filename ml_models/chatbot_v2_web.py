from transformers import pipeline

class WebChatbot:
    def __init__(self):
        """
        Initializes the text-generation chatbot pipeline and chat history.
        """
        self.chatbot = pipeline("text-generation", model="microsoft/DialoGPT-medium")
        self.chat_history = []

    def get_response(self, user_input):
        """
        Accepts user input string, returns bot response string and updates chat history.
        """
        # Append user input to chat history
        self.chat_history.append(user_input)

        # Generate response using text-generation pipeline
        # Join chat history as context
        context = " ".join(self.chat_history[-5:])  # last 5 messages as context
        outputs = self.chatbot(context, max_length=100, num_return_sequences=1)
        bot_response = outputs[0]['generated_text'][len(context):].strip()

        # Append bot response to chat history
        self.chat_history.append(bot_response)

        return bot_response, self.chat_history
