#!/usr/bin/env python3
import csv
import re
import sys
import requests
from bs4 import BeautifulSoup

INPUT = "./wordle_tables_clean.csv"
OUTPUT = "tables_with_new_data.csv"

def fetch_word_data(word):
    """Fetch year and etymology data for a word from Merriam-Webster."""
    word = word.lower()
    url = f"https://www.merriam-webster.com/dictionary/{word}"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching {word}: {e}", file=sys.stderr)
        return -1, "unknown", False
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Extract YEAR (returns year and accuracy flag)
    year, is_accurate = extract_year(soup, word)
    
    # Extract ETYMOLOGY
    etym = extract_etymology(soup, year)
    
    return year, etym, is_accurate

def extract_year(soup, word):
    """Extract year from first-known-content-section.
    
    Returns:
        tuple: (year, is_accurate) where year is an int and is_accurate is a bool
    """
    # Find the div with class containing 'first-known-content-section'
    first_known_div = soup.find('div', class_=lambda x: x and 'first-known-content-section' in x)
    
    if not first_known_div:
        print(f"No year found for {word}", file=sys.stderr)
        return -1, False
    
    # Find the p tag with classes 'ety-sl' and 'pb-3'
    year_p = first_known_div.find('p', class_=lambda x: x and 'ety-sl' in x and 'pb-3' in x)
    
    if not year_p:
        print(f"No year found for {word}", file=sys.stderr)
        return -1, False
    
    # Extract text
    text = year_p.get_text()
    
    # First, try to find an exact 3-4 digit year
    year_match = re.search(r'\b(\d{3,4})\b', text)
    if year_match:
        return int(year_match.group(1)), True
    
    # If no exact year, look for century notation (e.g., "13th century", "11th century")
    century_match = re.search(r'\b(\d{1,2})(?:st|nd|rd|th)\s+century\b', text, re.IGNORECASE)
    if century_match:
        century_num = int(century_match.group(1))
        # Convert century to start year (21st century -> 2000, 13th century -> 1200, etc.)
        year = (century_num - 1) * 100
        print(f"Found century for {word}: {century_num}th century -> {year}", file=sys.stderr)
        return year, False
    
    print(f"No year found for {word}", file=sys.stderr)
    return -1, False

def extract_etymology(soup, year):
    """Extract etymology from etymology-content-section."""
    # Find the div with class containing 'etymology-content-section'
    etym_div = soup.find('div', class_=lambda x: x and 'etymology-content-section' in x)
    
    if not etym_div:
        # No etymology section, classify based on year
        return classify_by_year(year)
    
    # Find the p tag with class 'et'
    etym_p = etym_div.find('p', class_='et')
    
    if not etym_p:
        # No etymology paragraph, classify based on year
        return classify_by_year(year)
    
    # Get text and strip HTML tags (get_text() handles this)
    etym_text = etym_p.get_text(separator=' ', strip=True)
    
    if etym_text:
        return etym_text
    else:
        return classify_by_year(year)

def classify_by_year(year):
    """Classify etymology based on year when no etymology text exists."""
    if year >= 1800:
        return "modern english"
    elif year > 1450 and year < 1800:
        return "early modern english"
    else:
        return "unknown"

def main():
    with open(INPUT, 'r', encoding='utf-8') as infile, \
         open(OUTPUT, 'w', encoding='utf-8', newline='') as outfile:
        
        reader = csv.reader(infile)
        writer = csv.writer(outfile)
        
        # Read and write header
        header = next(reader)
        writer.writerow(header + ['year_used', 'etym', 'year_accurate'])
        
        # Process each row
        for row in reader:
            if len(row) < 3:
                print(f"Skipping malformed row: {row}", file=sys.stderr)
                continue
            
            word = row[2]  # Column 3 (0-indexed as 2)
            print(f"Processing: {word}")
            
            year, etym, is_accurate = fetch_word_data(word)
            
            # Append new columns to the row
            writer.writerow(row + [year, etym, is_accurate])
    
    print(f"\nProcessing complete. Output written to {OUTPUT}")

if __name__ == "__main__":
    main()