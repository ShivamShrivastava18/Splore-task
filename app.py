from flask import Flask, render_template, request, jsonify, session
import google.generativeai as genai
from PIL import Image
import io
import base64
import hashlib

app = Flask(__name__)
genai.configure(api_key='YOUR GEMINI API KEY')
model = genai.GenerativeModel('gemini-2.0-flash-exp')

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
        image_data = request.form.get('image', '')
        user_prompt = request.form.get('prompt', '').strip()
        
        if image_data:
            image_binary = base64.b64decode(image_data.split(',')[1])
            
            current_image_hash = get_image_hash(image_binary)
            
            if 'last_image_hash' not in session or session['last_image_hash'] != current_image_hash:
                session.pop('portfolio_data', None)
                session['last_image_hash'] = current_image_hash
            
            img = Image.open(io.BytesIO(image_binary))
            
            if 'portfolio_data' not in session:
                response = model.generate_content([INITIAL_ANALYSIS_PROMPT, img])
                initial_analysis = response.text
                session['portfolio_data'] = initial_analysis
                
                if user_prompt:
                    follow_up = model.generate_content(
                        FOLLOWUP_PROMPT.format(
                            stored_data=initial_analysis,
                            user_question=user_prompt
                        )
                    )
                    return jsonify({'response': follow_up.text})
                
                return jsonify({'response': initial_analysis})
        
        if 'portfolio_data' in session and user_prompt:
            response = model.generate_content(
                FOLLOWUP_PROMPT.format(
                    stored_data=session['portfolio_data'],
                    user_question=user_prompt
                )
            )
            return jsonify({'response': response.text})
        
        if 'portfolio_data' not in session:
            return jsonify({
                'error': 'Please upload an image first',
                'status': 'error'
            }), 400
            
        return jsonify({'response': session['portfolio_data']})
            
    except Exception as e:
        return jsonify({
            'error': f"An error occurred: {str(e)}",
            'status': 'error'
        }), 400

@app.route('/reset', methods=['POST'])
def reset_analysis():
    session.clear()
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    app.run(debug=True)
