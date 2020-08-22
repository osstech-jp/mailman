============================
Listing membership via email
============================

A list of the members of a mailing list can be obtained via the ``who``
command.

The mail command ``who`` returns a list of selected members display names
and email addresses sorted by email addresss.

    >>> from mailman.commands.eml_who import Who
    >>> from mailman.utilities.string import wrap
    >>> who = Who()
    >>> print(who.name)
    who
    >>> print(wrap(who.description))
    Produces a list of member names and email addresses.
    <BLANKLINE>
    The optional delivery= and mode= arguments can be used to limit the
    report to those members with matching delivery status and/or delivery
    mode.  If either delivery= or mode= is specified more than once, only
    the last occurrence is used.

    >>> print(who.argument_description)
    [delivery=<enabled|disabled>] [mode=<digest|regular>]

Create a list with some members.

    >>> from mailman.app.lifecycle import create_list
    >>> mlist = create_list('alpha@example.com')
    >>> mlist.send_welcome_message = False
    >>> from mailman.testing.helpers import subscribe
    >>> cmember = subscribe(mlist, 'Cate')
    >>> dmember = subscribe(mlist, 'Doug')
    >>> amember = subscribe(mlist, 'Anne')
    >>> bmember = subscribe(mlist, 'Bart')
    >>> emember = subscribe(mlist, 'Elly')
    >>> fmember = subscribe(mlist, 'Fred')

Set Bart's delivery disabled and Elly's mode to digest.

    >>> from mailman.interfaces.member import DeliveryMode, DeliveryStatus
    >>> bmember.preferences.delivery_status = DeliveryStatus.by_moderator
    >>> emember.preferences.delivery_mode = DeliveryMode.mime_digests

Add an administrator.

    >>> from mailman.interfaces.member import MemberRole
    >>> imember = subscribe(mlist, 'Irma', role=MemberRole.owner)

A member requests a roser visible only to administrators.

    >>> from mailman.model.roster import RosterVisibility
    >>> mlist.member_roster_visibility = RosterVisibility.moderators
    >>> from mailman.runners.command import Results
    >>> results = Results()
    >>> from mailman.email.message import Message
    >>> msg = Message()
    >>> msg['From'] = amember.address.email
    >>> print(who.process(mlist, msg, {}, (), results))
    ContinueProcessing.no
    >>> print(results)
    The results of your email command are provided below.
    <BLANKLINE>
    You are not authorized to see the membership list.
    <BLANKLINE>

An administrator makes the same request.

    >>> results = Results()
    >>> msg = Message()
    >>> msg['From'] = imember.address.email
    >>> print(who.process(mlist, msg, {}, (), results))
    ContinueProcessing.yes
    >>> print(results)
    The results of your email command are provided below.
    <BLANKLINE>
    Members of the alpha@example.com mailing list:
        Anne Person <aperson@example.com>
        Bart Person <bperson@example.com>
        Cate Person <cperson@example.com>
        Doug Person <dperson@example.com>
        Elly Person <eperson@example.com>
        Fred Person <fperson@example.com>
    <BLANKLINE>

And again, but skipping those with disabled delivery or digests.

    >>> results = Results()
    >>> args = ['delivery=enabled', 'mode=regular']
    >>> print(who.process(mlist, msg, {}, args, results))
    ContinueProcessing.yes
    >>> print(results)
    The results of your email command are provided below.
    <BLANKLINE>
    Members of the alpha@example.com mailing list:
        Anne Person <aperson@example.com>
        Cate Person <cperson@example.com>
        Doug Person <dperson@example.com>
        Fred Person <fperson@example.com>
    <BLANKLINE>

And finally list just digest members.

    >>> results = Results()
    >>> args = ['mode=digest']
    >>> print(who.process(mlist, msg, {}, args, results))
    ContinueProcessing.yes
    >>> print(results)
    The results of your email command are provided below.
    <BLANKLINE>
    Members of the alpha@example.com mailing list:
        Elly Person <eperson@example.com>
    <BLANKLINE>
