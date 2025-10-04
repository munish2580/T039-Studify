import spacy
from transformers import pipeline
import random

# Load a spaCy model to help find key phrases (potential answers)
nlp = spacy.load("en_core_web_sm")

# Load the specialized pipelines
question_generator = pipeline("text2text-generation", model="valhalla/t5-base-qg-hl")
mask_filler = pipeline("fill-mask", model="bert-base-uncased")

def generate_quiz_v3(context: str) -> list:
    """
    Generates a multiple-choice quiz using a multi-pipeline approach.
    1. Extracts a potential answer.
    2. Generates a question for that answer.
    3. Generates distractors using a fill-mask model.
    """
    print("🤖 Analyzing text to find a key phrase for the answer...")
    
    # --- Step 1: Find a potential answer in the text ---
    doc = nlp(context)
    # Extract noun chunks or entities as potential answers
    potential_answers = [chunk.text for chunk in doc.noun_chunks if len(chunk.text.split()) > 1]
    if not potential_answers:
        print("Could not find suitable key phrases to use as an answer.")
        return []
    
    # Pick a random key phrase as our correct answer
    correct_answer = random.choice(potential_answers)
    print(f"✅ Selected Answer: '{correct_answer}'")

    # Find the sentence this answer came from
    input_sentence = ""
    for sent in doc.sents:
        if correct_answer in sent.text:
            input_sentence = sent.text
            break
    if not input_sentence:
        return [] # Should not happen if answer was found

    # --- Step 2: Generate a question for that answer ---
    print("🤖 Generating a question for the selected answer...")
    # The model expects the answer to be highlighted with <hl> tags
    qg_input = f"<hl> {correct_answer} <hl> {input_sentence}"
    generated_q = question_generator(qg_input, max_length=64)
    question = generated_q[0]['generated_text']
    print(f"✅ Generated Question: '{question}'")

    # --- Step 3: Generate distractors (incorrect options) ---
    print("🤖 Generating incorrect options (distractors)...")
    # Replace the answer in the sentence with a <mask> token
    masked_sentence = input_sentence.replace(correct_answer, mask_filler.tokenizer.mask_token)
    
    # Use the fill-mask model to predict words for the blank
    predictions = mask_filler(masked_sentence)
    
    # Filter predictions to get unique and different options
    distractors = []
    for pred in predictions:
        # Make sure the predicted token is not part of the correct answer
        if pred['token_str'].lower() not in correct_answer.lower():
            distractors.append(pred['token_str'])
    
    # We need 3 distractors
    if len(distractors) < 3:
        # Fallback if we don't get enough unique distractors
        distractors.extend(["none of the above", "all of the above", "a different process"])

    distractors = list(set(distractors))[:3] # Get 3 unique distractors

    # --- Final Assembly ---
    options = [correct_answer] + distractors
    random.shuffle(options) # Mix up the options

    quiz_item = {
        "question": question,
        "options": options,
        "correct_answer": correct_answer
    }
    
    return [quiz_item]


# --- Example Usage ---
if __name__ == "__main__":
    educational_text = """
    Photosynthesis is a crucial process used by plants, algae, and some bacteria to convert light energy into
    chemical energy, through a process that converts carbon dioxide and water into glucose (a sugar) and oxygen.
    This process is essential for life on Earth as it produces most of the planet's oxygen and serves as the
    primary source of energy for most ecosystems.
    """

    quiz = generate_quiz_v3(educational_text)

    if quiz:
        question_data = quiz[0]
        print("\n--- Generated Quiz (Robust Version) ---")
        print(f"Q: {question_data['question']}")
        for i, option in enumerate(question_data['options']):
            print(f"   {chr(65+i)}) {option}")
        print(f"\nCorrect Answer: {question_data['correct_answer']}")