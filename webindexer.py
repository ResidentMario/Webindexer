"""Rudimentary crawler for the CUNY Baruch College website. Outputs a CSV list of discovered URLs."""

import requests
import re
import csv
import time

start_time = time.time()
indexpage = "http://www.baruch.cuny.edu/azindex.html"

def getPage(url):
	"""Wrapper of a method provided by the requests library for retrieving web data."""
	return requests.get(url).text

def getURLfromIndex(str, i_s, i_f):
	"""This method takes a string, a starting index, and an ending index and returns an HTML-delimited string found by going on either side of that index until certain characters are found.
		For example, if you are at index 5 in the string ` 12 41-0512 `, this method will return 41-0512.
		This method will """
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
	
def getURLsOnPage(url, delimiter):
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
					ret.append(candidate)
			# This is the relative link case. In this case we have to add back the current URL ahead of the relative link in order for it to make sense.
			else:
				candidate = url + '/' + getDelimitedString(p, m.start() + 7, ['\'', '"', ' ', '<'], ['\'', '"', ' ', '>'])
				# Again, check for uniqueness.
				if candidate not in ret:
					ret.append(candidate)
	return ret
	
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

def listFixes(list):
	"""This method executes a bunch of fixes on the list of URLs returned by the crawler, fixing issues that occur."""
	i = 0
	while i < len(list):
		# iCal is a calender format we don't parse. Ex. `http://blogs.baruch.cuny.edu/fieldcenter/events/?ical=1`
		if '?ical=' in list[i]:
			list.pop(i)
			i-=1
		# CSS files are removed, obviously. Ex. `http://blogs.baruch.cuny.edu/fieldcenter/wp-content/plugins/cac-bp-admin-bar-mods/css/admin-bar.css?ver=4.3.1`
		elif '.css' in list[i]:
			list.pop(i)
			i-=1
		# PHP executables are interactive. Google scrapes these, but it's a little too much to ask of us... Ex. `http://blogs.baruch.cuny.edu/fieldcenter/xmlrpc.php`
		elif '.php' in list[i]:
			list.pop(i)
			i-=1
		# Sometimes pages are included multiple times: the base page and a heading of comments on the page. Eg.
		# `http://blogs.baruch.cuny.edu/sustainability/will-the-climate-really-benefit-from-natural-gas-fueled-trucks-and-buses/` and
		# `http://blogs.baruch.cuny.edu/sustainability/will-the-climate-really-benefit-from-natural-gas-fueled-trucks-and-buses/#respond`
		# are both returned. The latter needs to be cleaned off.
		# We're just going to assume that the base list[i] is included as well.
		elif '#' in list[i]:
			list.pop(i)
			i-=1
		# XML files. Ex. `http://blsci.baruch.cuny.edu/wp-includes/wlwmanifest.xml`
		elif '.xml' in list[i]:
			list.pop(i)
			i-=1
		# Image files. Ex. `http://blsci.baruch.cuny.edu/wp-content/uploads/2013/07/favicon.gif`
		elif '.gif' in list[i] or '.jpg' in list[i] or '.png' in list[i] or 'ico' in list[i]:
			list.pop(i)
			i-=1
		# Doubled, tripled, quadrupled braces make an appearance. Ex. `http://ctl.baruch.cuny.edu//mailto:kannan.mohan@baruch.cuny.edu`
		elif '//' in list[i][7:]:
			list.pop(i)
			i-=1
		# Mailing queries.
		elif 'mailto' in list[i]:
			list.pop(i)
			i-=1
		# .cgi files. Ex. `http://www.baruch.cuny.edu/azindex.html/cgi-bin/schedule/schedule.cgi`
		elif '.cgi' in list[i]:
			list.pop(i)
			i-=1
		# javascripts.
		elif 'javascript:' in list[i]:
			list.pop(i)
			i -= 1
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
	master = quickSort(getURLsOnPage(indexpage, 'baruch.cuny'))
	for p in master:
		master = mergesortedLists(master, quickSort(getURLsOnPage(p, 'baruch.cuny')))
		print(p, 'executed!')
	master = listFixes(master)
	return master

def commitURLsToFile(list, csvfile):
	"""This method stores the URLs in a file, and is the last step in the execution of this script. For the moment it stores output in a CSV file."""
	with open(csvfile, 'w') as fp:
		for item in list:
			print(item, file=fp)

def searchURLsTwoDeep(basepage):
	"""Method needs rewriting..."""
	master = quickSort(getURLsOnPage(basepage, 'baruch.cuny'))
	for p in master:
		nextMaster = listFixes(quickSort(getURLsOnPage(p, 'baruch.cuny')))
		for p2 in nextMaster:
			if p2 not in master:
				nextMaster = mergesortedLists(nextMaster, listFixes(quickSort(getURLsOnPage(p, 'baruch.cuny'))))
				print(p2, 'executed!')
		master = mergesortedLists(master, nextMaster)
		print(p, 'exhausted!')

u = getURLsInIndex()
prettyPrintList(u)
commitURLsToFile(u, 'urls.csv')
print("Done!")
# u = searchURLsTwoDeep()
# commitURLsToFile(u, 'urls.csv')
# print("Done!")

print("Execution time: ~%s seconds" %  format((time.time() - start_time), ".3f"))
