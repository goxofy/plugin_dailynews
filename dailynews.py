import re
import requests
import time
from bs4 import BeautifulSoup
from lxml import etree
from plugins import register, Plugin, Event, logger, Reply, ReplyType


@register
class DailyNews(Plugin):
    name = "dailynews"
    ifanrnews_url = "https://www.ifanr.com/category/ifanrnews"
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
            # Get post_id from the ifanrnews url
            response = requests.get(self.ifanrnews_url)
            if response.status_code == 200:
                html = response.text
                article_url = (etree.HTML(html).xpath('//*[@id="articles-collection"]/div[2]/div/div[1]/a[2]'))[0].get('href')
                post_id = re.search(r"\d+$", article_url).group()
           
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
            soup = BeautifulSoup(post_content, "html.parser")
            
            # 提取emoji和新闻标题
            emoji_tags = soup.find_all("p", style="float: left; margin-right: 6px; margin-bottom: 0; width: 30px;")
            title_tags = soup.find_all("div", style="margin-bottom: 0; width: 88%;")
            
            emojis = [tag.text.strip() for tag in emoji_tags]
            titles = [tag.p.text.strip() for tag in title_tags]
            
            # 提取链接
            links = []
            for title in titles:
                link_tag = soup.find("h3", text=title)
                if link_tag and link_tag.a:
                    link = link_tag.a["href"]
                    links.append(link)
                else:
                    links.append("NoURL")
            # 缩址          
            shortened_links = []
            for link in links:
                if link != "NoURL":
                    api_url = f"https://api.uomg.com/api/long2dwz?dwzapi=urlcn&url={link}"
                    response = requests.get(api_url)
                    data = response.json()
                    if data["code"] == 1:
                        shortened_link = data["ae_url"].replace("\\/", "/")
                        shortened_links.append(shortened_link)
                        time.sleep(0.8)
                    else:
                        shortened_links.append(link)
                else:
                    shortened_links.append("NoURL")
 
            # 组合输出 
            news_list = []
            for emoji, title, link in zip(emojis, titles, shortened_links):
                    news_list.append({'title': title, 'url': link, 'emoji': emoji})

            return news_list
        except Exception as e:
            logger.error(f"Error occurred while extracting news list: {str(e)}")
            return []

    def format_news_list(self, news_list) -> str:
        format_output = ""
        for news in news_list:
            link = news["url"]
            title = news["title"]
            emoji = news["emoji"]
            format_output += f"{emoji}{title} ({link})\n"

        return format_output