from datetime import datetime
import requests
from bs4 import BeautifulSoup
from database import OpportunityDatabase

main_repo = "https://github.com/SimplifyJobs/Summer2025-Internships"
offseason_repo = "https://github.com/SimplifyJobs/Summer2025-Internships/blob/dev/README-Off-Season.md"
newgrad_repo = "https://github.com/SimplifyJobs/New-Grad-Positions"

def fetch_github_opportunities(repo_url, test_date=None):
    try:
        response = requests.get(repo_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        opportunities = []
        tables = soup.find_all('table')
        current_company = ""

        current_date = datetime.now()
        target_year = current_date.year
        
        if test_date:
            target_date = datetime.strptime(test_date, "%B %d, %Y").strftime("%b %d")
            target_year = datetime.strptime(test_date, "%B %d, %Y").year
        else:
            target_date = datetime.now().strftime("%b %d")
            
        print(f"Searching for opportunities posted on: {target_date}")
        
        for table in tables:
            rows = table.find_all('tr')[1:]
            for row in rows:
                cols = row.find_all('td')
                
                # Valid repo table
                if len(cols) >= 5:

                    if repo_url == offseason_repo:
                        date_posted = cols[-1].text.strip()
                        company_text = cols[0].text.strip()
                        title = cols[1].text.strip()
                        location = cols[2].text.strip()
                        terms = cols[3].text.strip()
                        link = cols[4].find('a')['href'] if cols[4].find('a') else None
                        if link == None:
                            continue
                    
                    elif repo_url == main_repo:
                        date_posted = cols[4].text.strip()
                        company_text = cols[0].text.strip()
                        title = cols[1].text.strip()
                        location = cols[2].text.strip()
                        terms = "Summer 2025"
                        link = cols[3].find('a')['href'] if cols[3].find('a') else None
                        if link == None:
                            continue
                    
                    elif repo_url == newgrad_repo:
                        date_posted = cols[4].text.strip()
                        company_text = cols[0].text.strip()
                        title = cols[1].text.strip()
                        location = cols[2].text.strip()
                        terms = "New Grad"
                        link = cols[3].find('a')['href'] if cols[3].find('a') else None
                        if link == None:
                            continue
                    
                    # Handle company name for arrow cases
                    if company_text == "↳":
                        company = current_company
                    else:
                        company = company_text
                        current_company = company
                    
                    if date_posted == target_date:

                        full_date = datetime.strptime(f"{date_posted} {target_year}", "%b %d %Y").strftime("%B %d, %Y")

                        location_cell = cols[2]
                        locations = []
                        for text in location_cell.stripped_strings:
                            # Skip the "▼ locations" text
                            if not text.endswith('locations') and '▼' not in text:
                                locations.append(text.strip())
                        formatted_locations = '; '.join(locations)

                        opportunity = {
                            "company": company, 
                            "title": title,
                            "location": formatted_locations,
                            "link": link,
                            "date_posted": full_date,
                            "terms": terms,
                            "sponsorship": determine_sponsorship(title)  
                        }
                        opportunities.append(opportunity)

        return opportunities
    except Exception as e:
        print(f"Error fetching GitHub opportunities: {e}")
        return []

def determine_sponsorship(title):
    if "🛂" in title:
        return "No Sponsorship Available"
    elif "🇺🇸" in title:
        return "Requires U.S. Citizenship"
    else:
        return "Other"

def scrape_and_store():
    try:
        db = OpportunityDatabase()
        
        new_opportunities = (
            fetch_github_opportunities(offseason_repo) +
            fetch_github_opportunities(main_repo) +
            fetch_github_opportunities(newgrad_repo)
        )
        
        for opp in new_opportunities:
            if not db.opportunity_exists(opp):
                db.add_opportunity(opp)
                print(f"Added new opportunity: {opp['company']} - {opp['title']}")
                
    except Exception as e:
        print(f"Error in scraper: {e}")

if __name__ == "__main__":
    scrape_and_store()
