import os
import regsub 
import string
import mm_cfg, mm_utils
import htmlformat

class HTMLFormatter:
    def InitVars(self):
	self._template_dir = os.path.join(mm_cfg.TEMPLATE_DIR, 
					  self._internal_name)

    def GetMailmanFooter(self):
	owners_html = htmlformat.Container()
	for i in range(len(self.owner)):
	    owner = self.owner[i]
	    owners_html.AddItem(htmlformat.Link('mailto:%s' % owner, owner))
	    if i + 1 <> len(self.owner):
		owners_html.AddItem(', ')

	# Remove the .Format() when htmlformat conversion is done.
	return htmlformat.Container(
	    '<hr>',
	    htmlformat.Address(
		htmlformat.Container( 
		    'List run by ',
		    owners_html,
		    '<p>',
		    'HTML generated by ',
		    htmlformat.Link(mm_cfg.MAILMAN_URL, 
				    "Mailman v %s" % mm_cfg.VERSION)))).Format()

    def SnarfHTMLTemplate(self, file):
	filename = os.path.join(self._template_dir, file)
	f = open(filename,'r')
	str = f.read()
	f.close()
	return str

    def FormatUsers(self, digest):
	def NotHidden(x, s=self, v=mm_cfg.ConcealSubscription):
	    return not s.GetUserOption(x, v)

	if self.closed:
	    return 'Sorry, not available over the web.'
	if digest:
	    people = filter(NotHidden, self.digest_members)
	else:
	    people = filter(NotHidden, self.members)

	def FormatOneUser(person, me=self):
	    import htmlformat, os
	    return htmlformat.Link(os.path.join(me.GetScriptURL('options'),
						person), person)
	items = map(FormatOneUser, people) 
	# Just return the .Format() so this works until I finish
	# converting everything to htmlformat...
	return apply(htmlformat.UnorderedList, tuple(items)).Format()

    def FormatOptionButton(self, type, value, user):
	users_val = self.GetUserOption(user, type)
	if users_val == value:
	    checked = ' CHECKED'
	else:
	    checked = ''
	name = { mm_cfg.DontReceiveOwnPosts : "dontreceive",
		 mm_cfg.DisableDelivery : "disablemail",
		 mm_cfg.EnableMime : "plaintext",
		 mm_cfg.AcknowlegePosts : "ackposts",
		 mm_cfg.Digests : "digest",
		 mm_cfg.ConcealSubscription : "conceal"
	       }[type]
	import sys
	return '<input type=radio name="%s" value="%d"%s>' % (name, value, checked)
    def FormatDigestButton(self):
	if self.digest_is_default:
	    checked = ' CHECKED'
	else:
	    checked = ''
	return '<input type=radio name="digest" value="1"%s>' % checked

    def FormatUndigestButton(self):
	if self.digest_is_default:
	    checked = ''
	else:
	    checked = ' CHECKED'
	return '<input type=radio name="digest" value="0"%s>' % checked

    def FormatFormStart(self, name, extra=''):
	base_url = self.GetScriptURL(name)
	full_url = os.path.join(base_url, extra)
	return ('<FORM Method=POST ACTION="%s">' % full_url)

    def FormatArchiveAnchor(self):
	return '<a href="%s">' % self.GetScriptURL("archives")

    def FormatFormEnd(self):
	return '</FORM>'

    def FormatBox(self, name, size=20):
	return '<INPUT type="Text" name="%s" size="%d">' % (name, size)

    def FormatSecureBox(self, name):
	return '<INPUT type="Password" name="%s">' % name

    def FormatButton(self, name, text='Submit'):
	return '<INPUT type="Submit" name="%s" value="%s">' % (name, text)

    def ParseTags(self, template, replacements):
	text = self.SnarfHTMLTemplate(template)
	parts = regsub.splitx(text, '</?[Mm][Mm]-[^>]*>')
	i = 1
	while i < len(parts):
	    tag = string.lower(parts[i])
	    if replacements.has_key(tag):
		parts[i] = replacements[tag]
	    else:
		parts[i] = ''
	    i = i + 2
	return string.join(parts, '')

    # This needs to wait until after the list is inited, so let's build it
    # when it's needed only.
    def GetStandardReplacements(self):
	return { 
	    '<mm-mailman-footer>' : self.GetMailmanFooter(),
	    '<mm-list-name>' : self.real_name,
	    '<mm-email-user>' : self._internal_name,
	    '<mm-list-description>' : self.description,
	    '<mm-list-info>' : string.join(string.split(self.info, '\n'),
					   '<br>'),
	    '<mm-form-end>'  : self.FormatFormEnd(),
	    '<mm-archive>'   : self.FormatArchiveAnchor(),
	    '</mm-archive>'  : '</a>',
	    '<mm-regular-users>' : self.FormatUsers(0),
	    '<mm-digest-users>' : self.FormatUsers(1),
	    '<mm-num-reg-users>' : `len(self.members)`,
	    '<mm-num-digesters>' : `len(self.digest_members)`,
	    '<mm-num-members>' : (`len(self.members)`
				  + `len(self.digest_members)`),
	    '<mm-posting-addr>' : '%s' % self.GetListEmail(),
	    '<mm-request-addr>' : '%s' % self.GetRequestEmail(),
	    '<mm-owner>' : self.GetAdminEmail()
	    }
    
    def InitTemplates(self):
	def ExtensionFilter(item):
	    return item[-5:] == '.html'

	files = filter(ExtensionFilter, os.listdir(mm_cfg.TEMPLATE_DIR))
	mm_utils.MakeDirTree(self._template_dir)
	for filename in files:
	    file1 = open(os.path.join(mm_cfg.TEMPLATE_DIR, filename), 'r')
	    text = file1.read()
	    file1.close()
	    file2 = open(os.path.join(self._template_dir, filename), 'w+')
	    file2.write(text)
	    file2.close()
