from http.server import BaseHTTPRequestHandler
import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
import datetime

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # 1. Setup the Feed
        fg = FeedGenerator()
        fg.title('Letterboxd Popular This Week')
        fg.link(href='https://letterboxd.com/films/popular/this/week/', rel='alternate')
        fg.description('Most popular films on Letterboxd this week.')
        fg.language('en')

        # 2. Fetch the HTML
        target_url = "https://letterboxd.com/films/ajax/popular/this/week"
        # We need a User-Agent so Letterboxd knows we aren't a malicious bot
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; RSSBot/1.0; +http://localhost)'
        }
        
        try:
            response = requests.get(target_url, headers=headers)
            response.raise_for_status() # Check for errors
            
            # 3. Parse the HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all items with class "posteritem"
            items = soup.find_all(class_="posteritem")

            for item in items:
                # The attributes are actually inside the div *inside* the li
                # We look for the div that holds the data attributes
                div = item.find('div')
                
                if div:
                    # Extract Headline
                    title = div.get('data-item-full-display-name')
                    
                    # Extract Link (and prepend domain)
                    relative_link = div.get('data-item-link')
                    link = f"https://letterboxd.com{relative_link}"
                    
                    # Extract Image (Optional, but nice for RSS)
                    # The 'src' might be in the img tag inside the div
                    img_tag = div.find('img')
                    img_src = img_tag['src'] if img_tag else None

                    # 4. Add to Feed
                    fe = fg.add_entry()
                    fe.title(title)
                    fe.link(href=link)
                    # Use the link as the unique ID
                    fe.id(link)
                    
                    # Create a description with the poster image
                    description_html = f'<p>Film: {title}</p>'
                    if img_src:
                        description_html += f'<img src="{img_src}" />'
                    fe.description(description_html)

            # 5. Send Response
            self.send_response(200)
            self.send_header('Content-type', 'application/xml')
            self.end_headers()
            self.wfile.write(fg.rss_str(pretty=True))
            return

        except Exception as e:
            # Handle errors
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode())
            return
