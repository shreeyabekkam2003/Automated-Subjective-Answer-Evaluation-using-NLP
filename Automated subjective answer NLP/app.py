from flask import Flask, render_template, request, session, redirect, url_for
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import string
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import numpy as np
import pandas as pd
import spacy
import math
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes
from msrest.authentication import CognitiveServicesCredentials
import os
import time
from flask import jsonify

app = Flask(__name__)

# Set the secret key for session
app.secret_key = 'gJ%gyv$XN38^Z@Jqz!5E*YU&6b2CQ#eT'

# Load models and data
sbert_model = SentenceTransformer('paraphrase-MiniLM-L6-v2')
context_model = spacy.load("en_core_web_sm")
stop_words = set(stopwords.words('english'))
key_answers_df = pd.read_excel('Key_answers.xlsx')

# Define weights for similarity metrics
weight_length = 0.2
weight_semantic_similarity = 0.3
weight_conceptual_similarity = 0.2
weight_keyword_matching = 0.3



def preprocess_text(text):
    # Convert to lowercase
    text_lower = text.lower()

    # Tokenization
    tokens = word_tokenize(text_lower)

    # Removing stop words and punctuation
    tokens_filtered = [token for token in tokens if token.lower() not in stop_words]
    tokens_filtered = [token.translate(str.maketrans('', '', string.punctuation)) for token in tokens_filtered]
    tokens_filtered = [token for token in tokens_filtered if token.isalpha() or token.isdigit()]

    return ' '.join(tokens_filtered)



def calculate_semantic_similarity(student_answer, key_answer):

    # Embedding for student answer
    answer_embedding = sbert_model.encode(student_answer, convert_to_tensor=True).reshape(1,-1)

    # Embeddings for key answer
    key_answer_embedding = sbert_model.encode(key_answer, convert_to_tensor=True).reshape(1,-1)

    # Calculate cosine similarity
    semantic_similarity_score = cosine_similarity(answer_embedding, key_answer_embedding).mean()

    return semantic_similarity_score



def calculate_conceptual_similarity(student_answer, key_ans_1, key_ans_2, key_ans_3):
    
    if not student_answer:
        student_answer = ""
    if not key_ans_1:
        key_ans_1 = ""
    if not key_ans_2:
        key_ans_2 = ""
    if not key_ans_3:
        key_ans_3 = ""
            
    # Tokenize sentences using SpaCy
    student_tokens = context_model(student_answer)
    key1_tokens = context_model(key_ans_1)
    key2_tokens = context_model(key_ans_2)
    key3_tokens = context_model(key_ans_3)
    
    # Compute average vector representations for student answer
    student_vector = np.mean([token.vector for token in student_tokens if token.has_vector], axis=0)
    # Compute average vector representations for key answers
    key1_vector = np.mean([token.vector for token in key1_tokens if token.has_vector], axis=0)
    key2_vector = np.mean([token.vector for token in key2_tokens if token.has_vector], axis=0)
    key3_vector = np.mean([token.vector for token in key3_tokens if token.has_vector], axis=0)
    
    # Reshape arrays to 2D
    student_vector = np.array(student_vector).reshape(1, -1)
    key1_vector = np.array(key1_vector).reshape(1, -1)
    key2_vector = np.array(key2_vector).reshape(1, -1)
    key3_vector = np.array(key3_vector).reshape(1, -1)

    similarity_score_1 = similarity_score_2 = similarity_score_3 = 0

    # Calculate cosine similarity for each key answer
    if not np.isnan(student_vector).any() and not np.isnan(key1_vector).any():
        similarity_score_1 = cosine_similarity(student_vector, key1_vector)

    if not np.isnan(student_vector).any() and not np.isnan(key2_vector).any():
        similarity_score_2 = cosine_similarity(student_vector, key2_vector)

    if not np.isnan(student_vector).any() and not np.isnan(key3_vector).any():
        similarity_score_3 = cosine_similarity(student_vector, key3_vector)

    # Compute average similarity score
    average_similarity_score = max(similarity_score_1, similarity_score_2, similarity_score_3)
    
    return average_similarity_score



def extract_key_words(text):

    # Tokenize and analyze the text using SpaCy
    doc = context_model(text)
    
    # Initialize an empty set to store key words
    key_words = set()
    
    # Extract relevant tokens based on part-of-speech tags and dependency relationships
    for token in doc:
        if token.pos_ in ["NOUN", "PROPN", "ADJ"] and not token.is_stop :
            key_words.add(token.text.lower())  # Convert to lowercase for consistency
    
    return key_words



def calculate_keyword_matching_score(key_ans_1,key_ans_2,key_ans_3,answer):

    topic_keywords = []

    keys1 = extract_key_words(key_ans_1)
    keys2 = extract_key_words(key_ans_2)
    keys3 = extract_key_words(key_ans_3)

    topic_keywords = keys1.intersection(keys2, keys3) # Pick common key_words from 3 key answers

    matched_keywords = [keyword for keyword in topic_keywords if keyword in answer]

    # Calculate the matching score based on the number of matched keywords
    keyword_matching_score = len(matched_keywords) / len(topic_keywords)

    return keyword_matching_score



def calculate_length_similarity(student_answer, avg_key_answer_length):

    if len(student_answer) > avg_key_answer_length:
        length_difference = 0.1

    else:

        # Normalize lengths
        max_length = max(len(student_answer), avg_key_answer_length)
        normalized_student_length = len(student_answer) / max_length
        normalized_key_length = avg_key_answer_length / max_length

        # Calculate absolute length difference
        length_difference = abs(normalized_student_length - normalized_key_length)


    def score_func(x):
        return max(0, 1 - x)

    length_similarity_score = score_func(length_difference)

    return length_similarity_score



def evaluate_answer(student_answer, key_ans_1, key_ans_2, key_ans_3):

    # Preprocess the student answer
    preprocessed_answer = preprocess_text(student_answer)

    # Calculate semantic similarity scores for each key answer
    semantic_similarity_score_1 = calculate_semantic_similarity(preprocessed_answer, key_ans_1)
    semantic_similarity_score_2 = calculate_semantic_similarity(preprocessed_answer, key_ans_2)
    semantic_similarity_score_3 = calculate_semantic_similarity(preprocessed_answer, key_ans_3)

    # Calculate the average semantic similarity score
    semantic_similarity_scores = [semantic_similarity_score_1, semantic_similarity_score_2, semantic_similarity_score_3]
    non_empty_scores = [score for score in semantic_similarity_scores if score is not None]
    
    if not non_empty_scores:
        average_semantic_similarity_score = 0
    else:
        average_semantic_similarity_score = np.max(non_empty_scores)


    conceptual_similarity_score = calculate_conceptual_similarity(preprocessed_answer,key_ans_1,key_ans_2,key_ans_3)

    keyword_matching_score = calculate_keyword_matching_score(key_ans_1,key_ans_2,key_ans_3,preprocessed_answer)

    avg_key_answer_length = (len(key_ans_1) + len(key_ans_2) + len(key_ans_3)) / 3

    length_similarity_score = calculate_length_similarity(student_answer, avg_key_answer_length)

    if average_semantic_similarity_score < 0.2 or keyword_matching_score < 0.1:
        total_score = 0
    else:
        total_score = (
            weight_semantic_similarity * average_semantic_similarity_score +
            weight_conceptual_similarity * conceptual_similarity_score +
            weight_keyword_matching * keyword_matching_score +
            weight_length * length_similarity_score
        )

    factor=10**3
    ans=math.ceil(total_score*factor)/factor

    return round(float(ans*5),3)


def calculate_final_grade(total_score):

    # Heuristic grading logic for total score
    if total_score >=45:
        return "O : Outstanding"
    elif total_score >=40:
        return "A : Very Good"
    elif total_score >=30:
        return "B : Good"
    elif total_score >=17:
        return "C : Pass"
    else:
        return "F : Fail"



key_answers_df = pd.read_excel('Key_answers.xlsx')
key_ans_1 = key_answers_df['Key_ans_1']
key_ans_2 = key_answers_df['Key_ans_2']
key_ans_3 = key_answers_df['Key_ans_3']

# Define your Azure Cognitive Services credentials
subscription_key = os.environ["VISION_KEY"]
endpoint = os.environ["VISION_ENDPOINT"]

# Initialize the Computer Vision client
computervision_client = ComputerVisionClient(endpoint, CognitiveServicesCredentials(subscription_key))

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Check if the username and password are valid
        if username == 'admin' and password == 'password':
            # If valid, redirect to the upload page
            return redirect(url_for('upload'))
        else:
            # If not valid, render the login page again with an error message
            return render_template('index.html', error='Invalid username or password')

    return render_template('index.html',error='')


@app.route('/upload', methods=['GET','POST'])
def upload():
    # Check if the POST request has the file part
    if request.method == 'POST':
        # Handle file upload here
        file = request.files.get('image')
        if not file:
            # Process the file as needed
            return jsonify({'message': 'File uploaded failed'})

        # Save the uploaded image to a temporary location
        temp_image_path = os.path.join(app.root_path, 'temp_image.jpg')
        file.save(temp_image_path)

        # Call the Read API to extract text from the uploaded image
        with open(temp_image_path, 'rb') as image_file:
            read_response = computervision_client.read_in_stream(image_file, raw=True)
        read_operation_location = read_response.headers["Operation-Location"]
        operation_id = read_operation_location.split("/")[-1]

        # Wait for the operation to complete and get the results
        while True:
            read_result = computervision_client.get_read_result(operation_id)
            if read_result.status not in ['notStarted', 'running']:
                break
            time.sleep(1)

        # Process the extracted text result
        extracted_answers = process_extracted_text(read_result)
        print(extracted_answers)

        session['clear_answers']=True
        
        return render_template('ques.html', answers=extracted_answers)

    return render_template('upload.html')


def process_extracted_text(read_result):
    # Process the extracted text result to extract answers
    question_numbers = ["1", "2", "3", "4", "5", "6","7","8","9","10"]
    extracted_answers = {}

    if read_result.status == OperationStatusCodes.succeeded:
        current_question = None
        current_answer = ''
        for text_result in read_result.analyze_result.read_results:
            for line in text_result.lines:
                line_text = line.text.strip()
                for question_number in question_numbers:
                    if line_text.startswith(f"{question_number}."):
                        if current_question is not None:
                            extracted_answers[f'answer{current_question}'] = current_answer.strip()
                        current_question = question_number
                        current_answer = ''
                        break
                current_answer += line.text + '\n'
        if current_question is not None:
            extracted_answers[f'answer{current_question}'] = current_answer.strip()

    return extracted_answers



@app.route('/ques', methods=['GET', 'POST'])
def ques():
    session['answers']=session.get('answers',{})

    if session.get('clear_answers', False):
        # Clear answers from the session
        session['answers'] = {}
        # Reset the session variable
        session['clear_answers'] = False

    if request.method == 'POST':
        # Process the submitted answers and redirect to evaluate
        for i in range(1, 11):
            answer_key='answer'+str(i)
            session['answers'][answer_key] = request.form.get(answer_key, '')

        return redirect(url_for('evaluate')) 
    
    return render_template('ques.html', answers=session['answers'])

def sort_by_question_number(answers):
    return sorted(answers.items(), key=lambda x: int(x[0].split('answer')[1]))

# Register the custom filter with Jinja environment
app.jinja_env.filters['sort_by_question_number'] = sort_by_question_number

@app.route('/evaluate', methods=['GET', 'POST'])
def evaluate():
    answers=session.get('answers',{})

    if request.method == 'POST':
        return redirect(url_for('results'))
    
    return render_template('evaluate.html',answers=answers)


@app.route('/results', methods=['GET', 'POST'])
def results():
    if request.method == 'POST':
        total_score = 0
        detailed_results = []

        # Calculate total score and detailed results
        for i in range(1, 11):
            key1, key2, key3 = key_ans_1[i-1], key_ans_2[i-1], key_ans_3[i-1]
            student_answer = session['answers'].get(f'answer{i}', '')
            answer_score = evaluate_answer(student_answer, key1, key2, key3)
            total_score += answer_score
            detailed_results.append((f'Question {i}', answer_score))

        # Calculate final grade
        total_score=math.ceil(total_score)
        final_grade = calculate_final_grade(total_score)

        detailed_results_json = [list(item) for item in detailed_results]

        # Store data in session
        session['total_score'] = total_score
        session['final_grade'] = final_grade
        session['detailed_results'] = detailed_results_json
        session['show_results']=True

        return render_template('results.html', total_score=total_score, final_grade=final_grade, detailed_results=detailed_results_json,show_results=True)

    return render_template('results.html',show_results=False)



if __name__ == '__main__':
    app.run(debug=True)