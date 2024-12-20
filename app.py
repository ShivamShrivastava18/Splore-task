from flask import Flask, render_template, request, jsonify, session
import google.generativeai as genai
from PIL import Image
import io
import base64
import hashlib

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Required for session management
genai.configure(api_key='AIzaSyDQI0dSMeduv-yb95tfxwBfHJ1pJVP2Fc4')
model = genai.GenerativeModel('gemini-2.0-flash-exp')

# Initial analysis prompt
INITIAL_ANALYSIS_PROMPT = """Please analyze this investment portfolio image by summarizing the visual details. Extract and organize the following information explicitly present in the image:

1. **Portfolio Overview**:
   - Current value, invested value, total returns (including percentage), and XIRR.
   - Day-to-day changes, including returns and percentages.

2. **Asset Performance**:
   - Scheme names, categories, and specific metrics such as NAV, returns (%), and day changes.
   - Current values and any associated performance metrics.

3. **Visual Elements**:
   - Tables, charts, or graphs displayed, along with their labels or represented data.
   - Key patterns, distributions, or trends directly visible in the visuals.

4. **Key Observations**:
   - Highlight notable figures or metrics (e.g., significant positive or negative returns).
   - Identify any prominently displayed messages or warnings.

# Important Notes:
- Avoid making subjective assessments or inferences about the financial data.
- Focus solely on extracting and summarizing visible and verifiable details from the image.
- If critical details are missing from the image, specify the required information for a more comprehensive summary.

Provide an organized response based solely on the observable data while ensuring clarity and accuracy."""



FOLLOWUP_PROMPT = """Based on the previously analyzed portfolio data:

{stored_data}

Please specifically address this follow-up question: {user_question}

Provide a focused and concise response that directly answers the question without repeating the full portfolio analysis."""

def get_image_hash(image_data):
    """Generate a hash of the image data to identify unique images"""
    return hashlib.md5(image_data).hexdigest()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    try:
        # Get image data and user prompt
        image_data = request.form.get('image', '')
        user_prompt = request.form.get('prompt', '').strip()
        
        # If there's image data, process it
        if image_data:
            # Decode base64 image
            image_binary = base64.b64decode(image_data.split(',')[1])
            
            # Generate hash of the image
            current_image_hash = get_image_hash(image_binary)
            
            # Check if this is a new image
            if 'last_image_hash' not in session or session['last_image_hash'] != current_image_hash:
                # Clear previous analysis for new image
                session.pop('portfolio_data', None)
                session['last_image_hash'] = current_image_hash
            
            # Process the image
            img = Image.open(io.BytesIO(image_binary))
            
            # Generate initial analysis if needed
            if 'portfolio_data' not in session:
                response = model.generate_content([INITIAL_ANALYSIS_PROMPT, img])
                initial_analysis = response.text
                session['portfolio_data'] = initial_analysis
                
                # If there's a specific question, address it
                if user_prompt:
                    follow_up = model.generate_content(
                        FOLLOWUP_PROMPT.format(
                            stored_data=initial_analysis,
                            user_question=user_prompt
                        )
                    )
                    return jsonify({'response': follow_up.text})
                
                return jsonify({'response': initial_analysis})
        
        # Handle follow-up questions for existing analysis
        if 'portfolio_data' in session and user_prompt:
            response = model.generate_content(
                FOLLOWUP_PROMPT.format(
                    stored_data=session['portfolio_data'],
                    user_question=user_prompt
                )
            )
            return jsonify({'response': response.text})
        
        # If no image and no stored analysis, return error
        if 'portfolio_data' not in session:
            return jsonify({
                'error': 'Please upload an image first',
                'status': 'error'
            }), 400
            
        # Return stored analysis if no specific prompt
        return jsonify({'response': session['portfolio_data']})
            
    except Exception as e:
        return jsonify({
            'error': f"An error occurred: {str(e)}",
            'status': 'error'
        }), 400

@app.route('/reset', methods=['POST'])
def reset_analysis():
    # Clear all session data
    session.clear()
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    app.run(debug=True)