from .models import Post,Platform
from dotenv import load_dotenv
import openai, os

def telegram_post(topics: list, channel: bool = False, group: bool = False):
    load_dotenv()
    openai.api_key = os.getenv("OPENAI_API_KEY")
    for topic in topics:
        platform_type = "channel" if channel else "group"
        prompt = f"""
        Generate a high engagement and professional post about "{topic}" 
        specifically formatted for a Telegram {platform_type} post.
        Keep it concise, friendly, and engaging.
        """
        
        # Call your AI model here, e.g. OpenAI GPT
        content_response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        content = content_response.choices[0].message.content

        Post.objects.create(
            content=content,
            ai_generated=True,
            platform=f"telegram {platform_type}"
        )
        
        #then the api goes here
def generate_non_telegram_post(topics_with_platform: list, image: bool = False):
    openai.api_key = os.getenv("OPENAI_API_KEY")
    """
    topics_with_platform: list of tuples -> [(topic1, 'facebook'), (topic2, 'linkedin')]
    image: whether to generate an image along with the post
    """
    for topic, social_media in topics_with_platform:
        # Construct the prompt for AI
        if image:
            prompt = f"""
            Generate a high-engagement and professional post about "{topic}" 
            for {social_media} post style. Include a description for a professional content-based image.
            """
        else:
            prompt = f"""
            Generate a high-engagement and professional post about "{topic}"
            specifically formatted for {social_media}.
            """

        # Call your AI model here (e.g., OpenAI GPT)
        content_response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        content = content_response.choices[0].message.content

        # Optionally generate an image using AI if image=True
        image_url = None
        if image:
            image_prompt = f"Professional image representing the topic: {topic}"
            image_response = openai.Image.create(
                model="dall-e-3",
                prompt=image_prompt
            )
            image_url = image_response.data[0].url

        # Save to database
        platform_mapping = {
        'linkedin': Platform.LINKEDIN,
        'facebook page': Platform.FACEBOOK_PAGE,
        'instagram': Platform.INSTAGRAM
        }

        platform = platform_mapping.get(social_media.lower())
        if not platform:
            # skip invalid platforms or log error
            print(f"Invalid platform: {social_media}")
            return

        Post.objects.create(
            content=content,
            ai_generated=True,
            platform=platform,
            image=image_url
        )

topics = [
    ("How Pharmagebeya helps Ethiopian wholesalers expand their market reach", False),
    ("Pharmagebeya’s digital dashboard: Track orders and inventory efficiently", True)
]

generate_non_telegram_post([(topic, "facebook page") for topic, _ in topics], image=True)

