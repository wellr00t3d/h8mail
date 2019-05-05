#!/usr/bin/env python
from time import sleep
from utils.colors import colors as c
import requests
import json
import socket
import sys
import platform

class target():
	def __init__(self, email):
		self.headers = {
			'User-Agent': 'h8mail-v.1.0-OSINT-and-Education-Tool (PythonVersion={pyver}; Platform={platfrm})'.format(pyver=sys.version.split(" ")[0], 
			platfrm=platform.platform().split("-")[0])}
		self.email = email
		self.pwnd = False
		self.data = [()]

	def make_request(self, url, meth="GET", timeout=10, redirs=True, data=None, params=None):
		try:
			response = requests.request(url=url, headers=self.headers, method=meth, timeout=timeout, allow_redirects=redirs, data=data, params=params)
			# response = requests.request(url="http://127.0.0.1:8000", headers=self.headers, method=meth, timeout=timeout, allow_redirects=redirs, data=data, params=params)
			if response.status_code == 429:
				c.info_news(c, "Reached RATE LIMIT, sleeping")
				sleep(2.5)
		except Exception as ex:
			c.bad_news(c, "Request could not be made for "+ self.email)
			print(ex)
			print(response)
		return response

	def get_hibp(self):
		sleep(1.3)
		url = "https://haveibeenpwned.com/api/v2/breachedaccount/{}?truncateResponse=true".format(self.email)
		response = self.make_request(url)
		if response.status_code not in [200, 404]:
			c.bad_news(c, "Could not contact HIBP for " + self.email)
			print(response.status_code)
			print(response)
			return

		if response.status_code == 200:
			self.pwnd = True
			data = response.json()
			for d in data:  # Returned type is a dict of Name : Service
				for _, ser in d.items():
					self.data.append(("HIBP_PWNED_SRC", ser))
			
			c.good_news(c, "Found {num} breaches for {target} using HIBP".format(num=len(self.data)-1, target=self.email))

		elif response.status_code == 404:
			c.info_news(c, "No breaches found for {} using HIBP".format(self.email))
			self.pwnd = False
		else:
			c.bad_news(c, "HIBP: got API response code {code} for {target}".format(code=response.status_code, target=self.email))
			self.pwnd = False

	
	def get_hunterio_public(self):
		try:
			print(self.email)
			target_domain = self.email.split("@")[1]
			url = "https://api.hunter.io/v2/email-count?domain={}".format(target_domain)
			req = self.make_request(url)
			response = req.json()
			if response["data"]["total"] != 0:
				self.data.append(("HUNTER_PUB", response["data"]["total"]))
			c.good_news(c, "Found {num} related emails for {target} using hunter.io".format(num=response["data"]["total"], target=self.email))	
		except Exception as ex:
			c.bad_news(c, "HunterIO (pubic API) error: " + self.email)
			print(ex)

	def get_hunterio_private(self, api_key):
		try:
			target_domain = self.email.split("@")[1]
			url = "https://api.hunter.io/v2/domain-search?domain={target}&api_key={key}".format(target=target_domain, key=api_key)
			req = self.make_request(url)
			response = req.json()
			for e in response["data"]["emails"]:
				self.data.append(("HUNTER_RELATED", e["value"]))
		except Exception as ex:
			c.bad_news(c, "HunterIO (private API) error for {target}:".format(target=self.email))
			print(ex)

	def get_snusbase(self, api_url, api_key):
		try:
			url = api_url
			self.headers.update({"Authorization": api_key})
			payload = {"type": "email", "term": self.email}
			req = self.make_request(url, meth="POST", data=payload)
			response = req.json()
			for result in response["result"]:
				if result["password"]:
					self.data.append(("SNUS_PASSWORD", result["password"]))
				if result["hash"]:
					if result["salt"]:
						self.data.append(("SNUS_HASH_SALT", result["hash"].strip() + " : " + result["salt"].strip()))
					else:
						self.data.append(("SNUS_HASH", result["hash"]))
		except Exception as ex:
			c.bad_news(c, "Snusbase error with {target}".format(self.email))
			print(ex)