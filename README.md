# Webindexer
A simple, hand-written web crawler optimized for the CUNY Baruch College website, intended to be used for assisting in the construction of an IBM Watson corpus in PAF 4199.

Usage notes:
* Currently aspx pages are not included. The reason for this is that on some parts of the Baruch website, particularly the MFE site, they tend to loop forever, creating /monty/monty/monty/monty/.../ links. Unfortunately this means that other parts of the website, particularly Baruch Athletics, that rely heavily (entirely) on aspx pages, are not going to be picked up using this library. I will have to write a workaround for this at some point.
