import base64
import os
import requests

# Your OpenAI API key

# Function to encode an image to base64
def encode_image(image_path:str) -> str:
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# Function to analyze apartment images
def describe_apartment_images(api_key:str,
                              prompt_text:str,
                              model:str, 
                              image_detail:str,
                              max_tokens:int, 
                              image_dir:str,
                              ) -> str:
    
    image_files = [f for f in os.listdir(image_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    content = []

    # Detailed prompt
    prompt = {
        "type": "text",
        "text": prompt_text
    }
    content.append(prompt)

    # Add image content
    for file_name in image_files:
        image_path = os.path.join(image_dir, file_name)
        base64_image = encode_image(image_path)
        image_url = {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{base64_image}",
                "detail": f"{image_detail}"
            }
        }
        content.append(image_url)

    # Prepare the request
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    payload = {
        "model": f"{model}",
        "messages": [
            {
                "role": "user",
                "content": content
            }
        ],
        "max_tokens": max_tokens
    }
    response = requests.post(url = "https://api.openai.com/v1/chat/completions", 
                             headers=headers, 
                             json=payload)
    data = response.json()
    description = data['choices'][0]['message']['content']

    return description

description = describe_apartment_images(sample=False, api_key='asd')
print(description)