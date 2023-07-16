import re
import requests
from plugins import register, Plugin, Event, logger, Reply, ReplyType


@register
class DailyNews(Plugin):
    name = "dailynews"
    api_base_url = "https://sso.ifanr.com/api/v5/wp/article"

    def did_receive_message(self, event: Event):
        pass

    def will_generate_reply(self, event: Event):
        query = event.context.query
        if query == self.config.get("command"):
            event.reply = self.reply()
            event.bypass()

    def will_send_reply(self, event: Event):
        pass

    def help(self, **kwargs) -> str:
        return "Use the command #dailynews(or whatever you like set with command field in the config) to get daily news"

    def reply(self) -> Reply:
        reply = Reply(ReplyType.TEXT, "Failed to get daily news")
        try:
            # Get post_id from the first API
            response = requests.get(self.api_base_url + "/stats/?limit=1")
            if response.status_code == 200:
                data = response.json()
                post_id = data["objects"][0]["post_id"]

                # Get complete news list from the second API
                related_url = f"{self.api_base_url}/{post_id}/related"
                response = requests.get(related_url)
                if response.status_code == 200:
                    data = response.json()
                    news_list = self.extract_news_list(data)

                    if len(news_list) > 0:
                        formatted_news = self.format_news_list(news_list)
                        reply = Reply(ReplyType.TEXT, formatted_news)
                        return reply

            logger.error("Failed to fetch daily news")
        except Exception as e:
            logger.error(f"Error occurred while fetching daily news: {str(e)}")
        return reply
        
    def extract_news_list(self, data) -> list:
        try:
            # Extract post_content from the data
            post_content = data['objects'][0]['post_content']

            # Extract news titles and links using regular expressions
            pattern = r'<h3>< a href="(.*?)">(.*?)<\/a><\/h3>'
            matches = re.findall(pattern, post_content)

            # Generate a list of news with title and link
            news_list = []
            for match in matches:
                link = match[0]
                title = match[1]
                news_list.append({'title': title, 'url': link})

            return news_list
        except Exception as e:
            logger.error(f"Error occurred while extracting news list: {str(e)}")
            return []

    def format_news_list(self, news_list) -> str:
        markdown_output = ""
        for news in news_list:
            link = news["url"]
            title = news["title"]
            markdown_output += f"- [{title}]({link})\n"

        return markdown_output