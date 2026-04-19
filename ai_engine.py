import os
import json
import google.generativeai as genai
from typing import List, Dict

class AIEngine:
    def __init__(self, api_key: str = None):
        # გასაღების აღება settings.json-იდან, არგუმენტიდან ან გარემოს ცვლადიდან
        self.api_key = api_key or self._load_api_key()
        self.model = None
        
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-3.1-pro-preview')

    def _load_api_key(self):
        """ტვირთავს API გასაღებს settings.json ფაილიდან."""
        settings_path = os.path.join(os.path.dirname(__file__), "settings.json")
        try:
            if os.path.exists(settings_path):
                with open(settings_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("gemini_api_key", "")
        except Exception as e:
            print(f"Error loading settings.json: {e}")
        return os.getenv("GEMINI_API_KEY", "")

    def analyze_articles(self, articles: List[Dict], user_query: str = None) -> str:
        """
        აანალიზებს მუხლებს Gemini-ს მეშვეობით.
        """
        if not self.model:
            return "შეცდომა: Gemini API Key არ არის კონფიგურირებული."

        # კონტექსტის მომზადება
        context_text = ""
        for art in articles:
            context_text += f"\n--- {art['title']} - მუხლი {art['article_no']} ---\n{art['content']}\n"

        prompt = f"""
შენ ხარ პროფესიონალი ქართველი იურისტი. შენი ამოცანაა ამიხსნა ქვემოთ მოცემული მუხლები მარტივი, ადამიანური ენით.

წესები:
1. გამოიყენე მხოლოდ მოწოდებული მუხლების ტექსტი.
2. არ გამოიგონო გარე ფაქტები.
3. თუ მომხმარებელს აქვს კონკრეტული კითხვა, უპასუხე მას ამ მუხლების ჭრილში.
4. გამოიყენე Markdown ფორმატირება (Bold, Lists) პასუხის გასამარტივებლად.

მომხმარებლის მოთხოვნა: {user_query or "ამიხსენი ეს მუხლები ადამიანური ენით."}

მუხლების ტექსტი:
{context_text}
"""
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"AI ანალიზისას მოხდა შეცდომა: {str(e)}"

    def analyze_articles_stream(self, articles: List[Dict], user_query: str = None):
        """
        სტრიმინგ რეჟიმში აანალიზებს მუხლებს Gemini-ს მეშვეობით.
        აბრუნებს გენერატორს, რომელიც ნაწილ-ნაწილ აწვდის ტექსტს.
        """
        if not self.model:
            yield "შეცდომა: Gemini API Key არ არის კონფიგურირებული."
            return

        # კონტექსტის მომზადება
        context_text = ""
        for art in articles:
            context_text += f"\n--- {art['title']} - მუხლი {art['article_no']} ---\n{art['content']}\n"

        prompt = f"""
შენ ხარ პროფესიონალი ქართველი იურისტი. შენი ამოცანაა ამიხსნა ქვემოთ მოცემული მუხლები მარტივი, ადამიანური ენით.

წესები:
1. გამოიყენე მხოლოდ მოწოდებული მუხლების ტექსტი.
2. არ გამოიგონო გარე ფაქტები.
3. თუ მომხმარებელს აქვს კონკრეტული კითხვა, უპასუხე მას ამ მუხლების ჭრილში.
4. გამოიყენე Markdown ფორმატირება (Bold, Lists) პასუხის გასამარტივებლად.

მომხმარებლის მოთხოვნა: {user_query or "ამიხსენი ეს მუხლები ადამიანური ენით."}

მუხლების ტექსტი:
{context_text}
"""
        try:
            # სტრიმინგ რეჟიმში გამოძახება
            response = self.model.generate_content(prompt, stream=True)
            for chunk in response:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            yield f"\nAI ანალიზისას მოხდა შეცდომა: {str(e)}"

