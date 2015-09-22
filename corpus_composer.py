"""Just a test script for now, using the webindexer library."""
import time
from webindexer import domainSearch, commitURLsToFile, prettyPrintList

start_time = time.time()

# commitURLsToFile(domainSearch('zicklin', 'http://zicklin.baruch.cuny.edu/'), 'zicklin.csv')
commitURLsToFile(domainSearch('pressroom', 'http://www.baruch.cuny.edu/pressroom/pressreleases.htm'), 'press.csv')

print("Execution time: ~%s seconds" %  format((time.time() - start_time), ".3f"))
