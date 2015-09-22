"""Web crawler library for the CUNY Baruch College website. `domainSearch()` is the method of primary interest."""

import requests
import re
import csv

indexpage = "http://www.baruch.cuny.edu/azindex.html"

def getPage(url):
	"""Wrapper of a method provided by the requests library for retrieving web data."""
	return requests.get(url).text

def getURLfromIndex(str, i_s, i_f):
	"""This method takes a string, a starting index, and an ending index and returns an HTML-delimited string found by going on either side of that index until certain characters are found.
	For example, if you are at index 5 in the string ` 12 41-0512 `, this method will return 41-0512.
	This method is used to find complete URLs based on identifying snippets. In this case we search for `ahref=`, go forward 7 characters (the length of `ahref=`, plus 
	the ' or " delimiter, if one is present), and parse out the full URL string from there."""
	s = i_s
	f = i_f
	while s - 1 > 0 and str[s - 1] not in ['\'', '"', ' ', '>']:
		s -= 1
	while f + 1 < len(str) and str[f + 1] not in ['\'', '"', ' ', '<']:
		f += 1
	return str[s:f + 1]

def getDelimitedString(data, index, front_delimiters, back_delimiters):
	i_front = i_back = index
	while data[i_front - 1] not in front_delimiters:
		i_front -= 1
	while data[i_back + 1] not in back_delimiters:
		i_back += 1
	return data[i_front:i_back + 1]
	
def getURLsOnPage(url):
	"""This method, given a page URL and a URL snippet that acts as a delimiter to hunt with, returns a list of all URLs on the page that either:
	contain that snippet;
	or are relative HTML links to subpages of the current page."""
	ret = []
	p = getPage(url)
	for m in re.finditer('href=', p):
		# First remove the case in which the link is internal to the page. This filters out self-redirects like `<a href="#top">Go to top</a>.`
		# Note that 6 is the length of the string `href=`. Thus `m.start() + 6` is the beginning of the actual URL link, whatever it may be.
		if p[m.start() + 6] != '#':
			# With that done we now have to distinguish between full links and relative ones. First let's handle full links.
			# We can discover full links by checking to see that `http` is the first four characters of the link root.
			if 'http' == p[m.start() + 6:m.start() + 10]:
				candidate = getDelimitedString(p, m.start() + 7, ['\'', '"', ' ', '<'], ['\'', '"', ' ', '>'])
				# Be sure to throw out external links pointing outside of the Baruch website. Be sure to check for uniqueness.
				if 'baruch.cuny' in candidate and candidate not in ret:
					# Before appending we must must downgrade `https` links to `http` ones. The website uses a mix of both, but using both will mess with our sorting.
					if 'https' in candidate:
						candidate = candidate.replace('https', 'http')
					# In both a direct or relative link we can have two types of links pointing to the same place: `foo/bar` and `foo/bar/`.
					# To keep from doubling these let's drop the `/` character at the end of the URL, if one is present.
					if candidate[len(candidate) - 1] == '/':
						candidate = candidate[:len(candidate) - 1]
					ret.append(candidate)
			# This is the relative link case. In this case we have to add back the current URL ahead of the relative link in order for it to make sense.
			else:
				candidate = url + '/' + getDelimitedString(p, m.start() + 7, ['\'', '"', ' ', '<'], ['\'', '"', ' ', '>'])
				# Remove the `../` relative path if it is present.
				if '../' in candidate:
					candidate = candidate.replace('../', '')
				# Again: in both a direct or relative link we can have two types of links pointing to the same place: `foo/bar` and `foo/bar/`.
				# To keep from doubling these let's drop the `/` character at the end of the URL, if one is present.
				if candidate[len(candidate) - 1] == '/':
					candidate = candidate[:len(candidate) - 2]
				# Again, check for uniqueness.
				if candidate not in ret:
					ret.append(candidate)
	return listFixes(ret)
	
def prettyPrintList(l):
	"""List pretty-printer. Useful for debugging."""
	print('[')
	for i in range(0, len(l)):
		print(' ', i, (5 - len(str(i)))*' ', ':', l[i])
	print(']')
	
def mergesortedLists(master, single):
	"""Merges two already sorted lists.
	This method is meant for merging single pages' link lists with a running master copy. It's optimized for that case."""
	m_c = 0
	s_c = 0
	for item in single:
		while master[m_c] < item:
			if m_c == len(master) - 1:
				break
			else:
				m_c += 1
		# Only merge non-duplicates.
		if master[m_c] != item:
			master = master[:m_c] + [item] + master[m_c:]
	return master		
			
def quickSort(array):
	"""A standard quick-sort algorithm; snippet taken from http://stackoverflow.com/questions/18262306/quick-sort-with-python.
		Used in this script during list merging."""
	less = []
	equal = []
	greater = []
	if len(array) > 1:
		pivot = array[0]
		for x in array:
			if x < pivot:
				less.append(x)
			if x == pivot:
				equal.append(x)
			if x > pivot:
				greater.append(x)
		# Don't forget to return something!
		return quickSort(less)+equal+quickSort(greater)  # Just use the + operator to join lists
    # Note that you want equal ^^^^^ not pivot
	else:  # You need to handle the part at the end of the recursion - when you only have one element in your array, just return the array.
		return array

def serviceCheck(string):
	"""A helper method for the `listFixes(list)` method, below.
	This method returns True if a URL contains any `.ending` other than `.pdf`, `.html`, or `.htm`. It returns False otherwise.
	True results are then thrown out by listFixes."""
	chk = string.rfind('/')
	if chk == -1:
		return False
	elif '.' not in string[chk:]:
		return False
	else:
		if '.pdf' not in string[chk:] and '.html' not in string[chk:] and '.htm' not in string[chk:]:
			return True
		
def listFixes(list):
	"""This method executes a bunch of fixes on the list of URLs returned by the crawler, fixing issues that occur."""
	i = 0
	while i < len(list):
		# Characters associated with page-serving (`?`, `:`, `//`, and `#`) are deleted from the list.
		# `?` indicates interactive content. This has a bad tendency of causing infinite loops: one page on the MFE subsite came to /monty/monty/monty/...
		# `:` indicates a script of some sort, usually one of the following: `javascript:`, `tel:`, or `mailto:`.
		# `#` indicates an internal link. There's no need to include a document multiple times, once for each section linked to!
		if '?' in list[i] or ':' in list[i][7:] or '#' in list[i] or '//' in list[i][7:]:
			# print(list[i], 'deleted!')
			list.pop(i)
			i-=1
		# Most pages containing the character `.` are also not good for our purposes. This is stuff like `.aspx` and `.css`.
		# However there are a couple of `.` containers we want to keep: `.pdf`, `.html`, `.htm`. So we include these manually.
		# This is a decently complex operation. The `serviceCheck(string)` method, defined directly above, is used to accomplish it.
		elif serviceCheck(list[i]):
			# print(list[i], 'deleted!')
			list.pop(i)
			i-=1
		# We we want to exclude URLs with `/feed` in them, like eg. `http://mfe.baruch.edu/feed/atom`. These cannot be parsed.
		elif '/feed' in list[i]:
			list.pop(i)
			i-=1
		# A mass domain that's not very useful: all pages with the predicate `http://blogs.baruch.cuny.edu/members/` Ex. `http://blogs.baruch.cuny.edu/members/z-wong/`
		elif 'http://blogs.baruch.cuny.edu/members/' in list[i]:
			list.pop(i)
			i -= 1
		# Similar. Ex. `http://ctl.baruch.cuny.edu/author/csilsby/`
		elif 'http://ctl.baruch.cuny.edu/author/' in list[i]:
			list.pop(i)
			i -= 1
		i += 1
	return list
		
def getURLsInIndex():
	"""This method lists all pages linked to by subpages of the index page, as well as the index page itself.
	It's a test method intended to ensure that the script is operating efficiently."""
	master = quickSort(getURLsOnPage(indexpage))
	for p in master:
		master = mergesortedLists(master, quickSort(getURLsOnPage(p)))
		print(p)
	master = listFixes(master)
	return master

def commitURLsToFile(list, csvfile):
	"""This method stores the URLs in a CSV file."""
	with open(csvfile, 'w') as fp:
		for item in list:
			print(item, file=fp)
	print('File saved to', csvfile)

def enumerateFacultyManual():
	"""This method returns a list of pages within the Baruch faculty manual, taken off of one page.
	Also a test method."""
	ret = []
	for url in getURLsOnPage('http://www.baruch.cuny.edu/facultyhandbook/topics.htm'):
		if 'facultyhandbook' in url:
			ret += [url]
	return ret

def domainSearch(delimiter, starting_page):
	"""Wrapper method for the recursive page discovery crawler. This is the primary method meant to be called when using this library."""
	return quickSort(_domainSearch(delimiter, starting_page, []))
	
def _domainSearch(delimiter, page, list_of_pages_so_far):
	urls = getURLsOnPage(page)
	for url in urls:
		# Check that URL is valid. If so, include it.
		if delimiter in url and url not in list_of_pages_so_far:
			print(url)
			# PDFs won't give us back any links because of their encoding so there's no point trying to read them for links.
			# In fact, doing so will slow down the process a lot.
			# So we exclude them using an if check.
			if '.pdf' in url:
				list_of_pages_so_far += [url]
			else:
				# TODO: Check to remove the equivalent `foo/bar/` if `foo/bar` is present.
				list_of_pages_so_far = _domainSearch(delimiter, url, list_of_pages_so_far + [url])
	return list_of_pages_so_far
