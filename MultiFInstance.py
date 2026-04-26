import subprocess
import sys

if getattr(sys, "frozen", False):
    import os as _os, shutil as _shutil

    _orig_rmtree  = _shutil.rmtree
    _orig_rmdir   = _os.rmdir
    _orig_unlink  = _os.unlink

    def _silent_rmtree(path, *a, **kw):
        try: _orig_rmtree(path, *a, **kw)
        except Exception: pass

    def _silent_rmdir(path):
        try: _orig_rmdir(path)
        except Exception: pass

    def _silent_unlink(path):
        try: _orig_unlink(path)
        except Exception: pass

    _shutil.rmtree = _silent_rmtree
    _os.rmdir      = _silent_rmdir
    _os.unlink     = _silent_unlink

def _ensure_deps():
    if getattr(sys, "frozen", False):
        return

    CREATE_NO_WINDOW = 0x08000000
    required = [
        ("Pillow",  "PIL"),
        ("pywin32", "win32gui"),
        ("psutil",  "psutil"),
    ]
    for pkg, imp in required:
        try:
            __import__(imp)
        except ImportError:
            try:
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", pkg, "--quiet"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                )
                if pkg == "pywin32":
                    try:
                        subprocess.check_call(
                            [sys.executable, "-m", "pywin32_postinstall", "-install"],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            creationflags=CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                        )
                    except Exception:
                        pass
            except Exception:
                pass

_ensure_deps()

import tkinter as tk
from tkinter import ttk
import webbrowser
import threading
import time
import urllib.request
import urllib.error
import urllib.parse
import json
import io
import os
import glob
import re
import ctypes

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


def _load_embedded_image(b64_str, size):
    """Decode a base64 image string and return an ImageTk.PhotoImage at (size,size)."""
    if not PIL_AVAILABLE:
        return None
    try:
        import base64 as _b64, io as _io
        data  = _b64.b64decode(b64_str)
        img   = Image.open(_io.BytesIO(data)).convert("RGBA").resize((size, size), Image.LANCZOS)
        return ImageTk.PhotoImage(img)
    except Exception:
        return None


_ICON_B64_DASHBOARD = "iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAAz0lEQVR4nO3ZQQ6DMAxEUYf73zldsaRxhOVfNf+tkT0awQZHSJKkU42dh+ec89WyMdL7unZd2YFvA+3M6NyVKqAiUHZW566IRAGVgVYzO3fd0p/Av7IAOgDNAugANAugA9AsgA5AswA6AM0C6AA0C6AD0JYF7PzGynqa2bnrlnoDKoOtZnXuitj4BCqCZWd07pKko3kayw70NFbE09iXmZ7GABZAB6BZAB2AZgF0AJoF0AFoFkAHoFkAHYBmAXQAmqexiiE7PI392C5Jkg72AdTkcFfqNJ9jAAAAAElFTkSuQmCC"
_ICON_B64_USER = "iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAABLUlEQVR4nO2ZwRICIQxDwf//ZzxxYWZVIGnqNO/qbJuGsCq0ZowxxpiqdEXTMcZ4+qz3HqoptNmnwVeijAhpsjP4CtuIF7N4a3fDI57/BtUAlHimCTQD0KJZJtC3QHYoBrBWi1HXCUAXZL+10fWdALUANTZALUCNDVALUAM3gP3vDV3fCWAUZaWAUdcJYBVGrxYrVdQEoEQzX6z0LXArnv6twiy+UvZUeCXTvUB5wt3+ZRtEpqD8xQi1OPL46u9+B5S+Fyh9LF76VJg9PKMPzICo4dH9IAZED4/se22AanhUfx+I3DysXv3JjY5jA7IMPznV4y2gFqDmyIBs8Z+c6HIC1ALUbBuQNf6TXX1OgFqAGhugFqDGBqgFqLEBagFqbIBagJptA7JfX+/qewNfqaAXtAdOagAAAABJRU5ErkJggg=="
_ICON_B64_ACTIVITY = "iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAAyklEQVR4nO3YwQ6DIBQFUWj6/7+MqyZN0wRBYB5hzlrhesWgpiRJkiRJkiTpJHn1hKWUUjsm57ws17KJ7lz4rxVFvGZPEN2SAnru/pPzWrgC6AA0C6AD0N50gB4j3yW2KqBlV/gcWyvi+EdgmwJmvUtsU8AsFkAHoB1fQNM2GO1bfoRbBczYf6M4/hGoFhD5W34EVwAdgGYBdACaBdABaBZAB6BZAB2AZgF0AJoF0AFo1QJ6f2x8nxdljH+OXwFNrY74JxhlDEmSlC7SdURInH0LhgAAAABJRU5ErkJggg=="
_ICON_B64_DISCORD = "iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAABR0lEQVR4nO2awRLDIAhEtdP//2V76HjJqCCsIcZ91yrCupLUNiVCCCGEEHIm2TO5lFJQiXjJOZtqMU16UuFXZoWYGvzkwq9ohfhoA+5UfEr6fFUC7FZ8RZO3KMCuxVek/NVH4K0MBdh99yujOr4L1mt1X4+Q6Hhi8P8K87uveezMxETHaz4aUT1A+z4RNa4LmyAgxuwuSOPR8YbQAc75VvV789DxROiA6ASioQDRCUTjFcD6Stqbh44nQgcAYsyqL41HxxtCB4DiaHchalwX5H1ATQb1/R0dr8mKCxH0LdLSWyn2gOgEoqEA0QlEQwGiE4imK4D19/an0quHDhh9+BYXjOqgA6QBu7tAyl/lgF1F0OStPgK7iaDN9/h/iR3fBM22brngzmOCWv94B5gFuKp9d5NErX+8A9xEPxG869MBhBBCyLn8AACBWmnP/MbbAAAAAElFTkSuQmCC"
_ICON_B64_URL = "iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAA5ElEQVR4nO3ZwRKDMAhF0aT//8900bpKYskM4TH1nq1OIFjBamsAAAAAAAAAnqTvnGxmFha4963Yp7iSiNz4kIC4ELfBT258SERUiNfqQObmFfEuywI8xbQAqquhiDu97+4SibhXMzbqzXM46fTmPXEi/crZ3QOiu3RW17ev1XFZE6wyZZgC3hMjr1ilKVNuCmSvv12A06Kao7cI01tA9VweGde7Fk1wdSD7V1Du32Brn6QyH1gU68neCK2UmAKnVZoykiZYacowBVSBq0yZEq+mlW+dSxTg8o/fHQAAAAAAAIBi3tsJeCiYU2QIAAAAAElFTkSuQmCC"

_ICON_B64_MAP = {
    "dashboard":     _ICON_B64_DASHBOARD,
    "accounts":      _ICON_B64_USER,
    "instances":     _ICON_B64_URL,
    "biome_actions": _ICON_B64_ACTIVITY,
    "discord":       _ICON_B64_DISCORD,
}

_LICENSE_TEXT = """\
                    GNU GENERAL PUBLIC LICENSE
                       Version 3, 29 June 2007

 Copyright (C) 2007 Free Software Foundation, Inc. <https://fsf.org/>
 Everyone is permitted to copy and distribute verbatim copies
 of this license document, but changing it is not allowed.

                            Preamble

  The GNU General Public License is a free, copyleft license for
software and other kinds of works.

  The licenses for most software and other practical works are designed
to take away your freedom to share and change the works.  By contrast,
the GNU General Public License is intended to guarantee your freedom to
share and change all versions of a program--to make sure it remains free
software for all its users.  We, the Free Software Foundation, use the
GNU General Public License for most of our software; it applies also to
any other work released this way by its authors.  You can apply it to
your programs, too.

  When we speak of free software, we are referring to freedom, not
price.  Our General Public Licenses are designed to make sure that you
have the freedom to distribute copies of free software (and charge for
them if you wish), that you receive source code or can get it if you
want it, that you can change the software or use pieces of it in new
free programs, and that you know you can do these things.

  To protect your rights, we need to prevent others from denying you
these rights or asking you to surrender the rights.  Therefore, you have
certain responsibilities if you distribute copies of the software, or if
you modify it: responsibilities to respect the freedom of others.

  For example, if you distribute copies of such a program, whether
gratis or for a fee, you must pass on to the recipients the same
freedoms that you received.  You must make sure that they, too, receive
or can get the source code.  And you must show them these terms so they
know their rights.

  Developers that use the GNU GPL protect your rights with two steps:
(1) assert copyright on the software, and (2) offer you this License
giving you legal permission to copy, distribute and/or modify it.

  For the developers' and authors' protection, the GPL clearly explains
that there is no warranty for this free software.  For both users' and
authors' sake, the GPL requires that modified versions be marked as
changed, so that their problems will not be attributed erroneously to
authors of previous versions.

  Some devices are designed to deny users access to install or run
modified versions of the software inside them, although the manufacturer
can do so.  This is fundamentally incompatible with the aim of
protecting users' freedom to change the software.  The systematic
pattern of such abuse occurs in the area of products for individuals to
use, which is precisely where it is most unacceptable.  Therefore, we
have designed this version of the GPL to prohibit the practice for those
products.  If such problems arise substantially in other domains, we
stand ready to extend this provision to those domains in future versions
of the GPL, as needed to protect the freedom of users.

  Finally, every program is threatened constantly by software patents.
States should not allow patents to restrict development and use of
software on general-purpose computers, but in those that do, we wish to
avoid the special danger that patents applied to a free program could
make it effectively proprietary.  To prevent this, the GPL assures that
patents cannot be used to render the program non-free.

  The precise terms and conditions for copying, distribution and
modification follow.

                       TERMS AND CONDITIONS

  0. Definitions.

  "This License" refers to version 3 of the GNU General Public License.

  "Copyright" also means copyright-like laws that apply to other kinds of
works, such as semiconductor masks.

  "The Program" refers to any copyrightable work licensed under this
License.  Each licensee is addressed as "you".  "Licensees" and
"recipients" may be individuals or organizations.

  To "modify" a work means to copy from or adapt all or part of the work
in a fashion requiring copyright permission, other than the making of an
exact copy.  The resulting work is called a "modified version" of the
earlier work or a work "based on" the earlier work.

  A "covered work" means either the unmodified Program or a work based
on the Program.

  To "propagate" a work means to do anything with it that, without
permission, would make you directly or secondarily liable for
infringement under applicable copyright law, except executing it on a
computer or modifying a private copy.  Propagation includes copying,
distribution (with or without modification), making available to the
public, and in some countries other activities as well.

  To "convey" a work means any kind of propagation that enables other
parties to make or receive copies.  Mere interaction with a user through
a computer network, with no transfer of a copy, is not conveying.

  An interactive user interface displays "Appropriate Legal Notices"
to the extent that it includes a convenient and prominently visible
feature that (1) displays an appropriate copyright notice, and (2)
tells the user that there is no warranty for the work (except to the
extent that warranties are provided), that licensees may convey the
work under this License, and how to view a copy of this License.  If
the interface presents a list of user commands or options, such as a
menu, a prominent item in the list meets this criterion.

  1. Source Code.

  The "source code" for a work means the preferred form of the work
for making modifications to it.  "Object code" means any non-source
form of a work.

  A "Standard Interface" means an interface that either is an official
standard defined by a recognized standards body, or, in the case of
interfaces specified for a particular programming language, one that
is widely used among developers working in that language.

  The "System Libraries" of an executable work include anything, other
than the work as a whole, that (a) is included in the normal form of
packaging a Major Component, but which is not part of that Major
Component, and (b) serves only to enable use of the work with that
Major Component, or to implement a Standard Interface for which an
implementation is available to the public in source code form.  A
"Major Component", in this context, means a major essential component
(kernel, window system, and so on) of the specific operating system
(if any) on which the executable work runs, or a compiler used to
produce the work, or an object code interpreter used to run it.

  The "Corresponding Source" for a work in object code form means all
the source code needed to generate, install, and (for an executable
work) run the object code and to modify the work, including scripts to
control those activities.  However, it does not include the work's
System Libraries, or general-purpose tools or generally available free
programs which are used unmodified in performing those activities but
which are not part of the work.  For example, Corresponding Source
includes interface definition files associated with source files for
the work, and the source code for shared libraries and dynamically
linked subprograms that the work is specifically designed to require,
such as by intimate data communication or control flow between those
subprograms and other parts of the work.

  The Corresponding Source need not include anything that users
can regenerate automatically from other parts of the Corresponding
Source.

  The Corresponding Source for a work in source code form is that
same work.

  2. Basic Permissions.

  All rights granted under this License are granted for the term of
copyright on the Program, and are irrevocable provided the stated
conditions are met.  This License explicitly affirms your unlimited
permission to run the unmodified Program.  The output from running a
covered work is covered by this License only if the output, given its
content, constitutes a covered work.  This License acknowledges your
rights of fair use or other equivalent, as provided by copyright law.

  You may make, run and propagate covered works that you do not
convey, without conditions so long as your license otherwise remains
in force.  You may convey covered works to others for the sole purpose
of having them make modifications exclusively for you, or provide you
with facilities for running those works, provided that you comply with
the terms of this License in conveying all material for which you do
not control copyright.  Those thus making or running the covered works
for you must do so exclusively on your behalf, under your direction
and control, on terms that prohibit them from making any copies of
your copyrighted material outside their relationship with you.

  Conveying under any other circumstances is permitted solely under
the conditions stated below.  Sublicensing is not allowed; section 10
makes it unnecessary.

  3. Protecting Users' Legal Rights From Anti-Circumvention Law.

  No covered work shall be deemed part of an effective technological
measure under any applicable law fulfilling obligations under article
11 of the WIPO copyright treaty adopted on 20 December 1996, or
similar laws prohibiting or restricting circumvention of such
measures.

  When you convey a covered work, you waive any legal power to forbid
circumvention of technological measures to the extent such circumvention
is effected by exercising rights under this License with respect to
the covered work, and you disclaim any intention to limit operation or
modification of the work as a means of enforcing, against the work's
users, your or third parties' legal rights to forbid circumvention of
technological measures.

  4. Conveying Verbatim Copies.

  You may convey verbatim copies of the Program's source code as you
receive it, in any medium, provided that you conspicuously and
appropriately publish on each copy an appropriate copyright notice;
keep intact all notices stating that this License and any
non-permissive terms added in accord with section 7 apply to the code;
keep intact all notices of the absence of any warranty; and give all
recipients a copy of this License along with the Program.

  You may charge any price or no price for each copy that you convey,
and you may offer support or warranty protection for a fee.

  5. Conveying Modified Source Versions.

  You may convey a work based on the Program, or the modifications to
produce it from the Program, in the form of source code under the
terms of section 4, provided that you also meet all of these conditions:

    a) The work must carry prominent notices stating that you modified
    it, and giving a relevant date.

    b) The work must carry prominent notices stating that it is
    released under this License and any conditions added under section
    7.  This requirement modifies the requirement in section 4 to
    "keep intact all notices".

    c) You must license the entire work, as a whole, under this
    License to anyone who comes into possession of a copy.  This
    License will therefore apply, along with any applicable section 7
    additional terms, to the whole of the work, and all its parts,
    regardless of how they are packaged.  This License gives no
    permission to license the work in any other way, but it does not
    invalidate such permission if you have separately received it.

    d) If the work has interactive user interfaces, each must display
    Appropriate Legal Notices; however, if the Program has interactive
    interfaces that do not display Appropriate Legal Notices, your
    work need not make them do so.

  A compilation of a covered work with other separate and independent
works, which are not by their nature extensions of the covered work,
and which are not combined with it such as to form a larger program,
in or on a volume of a storage or distribution medium, is called an
"aggregate" if the compilation and its resulting copyright are not
used to limit the access or legal rights of the compilation's users
beyond what the individual works permit.  Inclusion of a covered work
in an aggregate does not cause this License to apply to the other
parts of the aggregate.

  6. Conveying Non-Source Forms.

  You may convey a covered work in object code form under the terms
of sections 4 and 5, provided that you also convey the
machine-readable Corresponding Source under the terms of this License,
in one of these ways:

    a) Convey the object code in, or embodied in, a physical product
    (including a physical distribution medium), accompanied by the
    Corresponding Source fixed on a durable physical medium
    customarily used for software interchange.

    b) Convey the object code in, or embodied in, a physical product
    (including a physical distribution medium), accompanied by a
    written offer, valid for at least three years and valid for as
    long as you offer spare parts or customer support for that product
    model, to give anyone who possesses the object code either (1) a
    copy of the Corresponding Source for all the software in the
    product that is covered by this License, on a durable physical
    medium customarily used for software interchange, for a price no
    more than your reasonable cost of physically performing this
    conveying of source, or (2) access to copy the
    Corresponding Source from a network server at no charge.

    c) Convey individual copies of the object code with a copy of the
    written offer to provide the Corresponding Source.  This
    alternative is allowed only occasionally and noncommercially, and
    only if you received the object code with such an offer, in accord
    with subsection 6b.

    d) Convey the object code by offering access from a designated
    place (gratis or for a charge), and offer equivalent access to the
    Corresponding Source in the same way through the same place at no
    further charge.  You need not require recipients to copy the
    Corresponding Source along with the object code.  If the place to
    copy the object code is a network server, the Corresponding Source
    may be on a different server (operated by you or a third party)
    that supports equivalent copying facilities, provided you maintain
    clear directions next to the object code saying where to find the
    Corresponding Source.  Regardless of what server hosts the
    Corresponding Source, you remain obligated to ensure that it is
    available for as long as needed to satisfy these requirements.

    e) Convey the object code using peer-to-peer transmission, provided
    you inform other peers where the object code and Corresponding
    Source of the work are being offered to the general public at no
    charge under subsection 6d.

  A separable portion of the object code, whose source code is excluded
from the Corresponding Source as a System Library, need not be
included in conveying the object code work.

  A "User Product" is either (1) a "consumer product", which means any
tangible personal property which is normally used for personal, family,
or household purposes, or (2) anything designed or sold for incorporation
into a dwelling.  In determining whether a product is a consumer product,
doubtful cases shall be resolved in favor of coverage.  For a particular
product received by a particular user, "normally used" refers to a
typical or common use of that class of product, regardless of the status
of the particular user or of the way in which the particular user
actually uses, or expects or is expected to use, the product.  A product
is a consumer product regardless of whether the product has substantial
commercial, industrial or non-consumer uses, unless such uses represent
the only significant mode of use of the product.

  "Installation Information" for a User Product means any methods,
procedures, authorization keys, or other information required to install
and execute modified versions of a covered work in that User Product from
a modified version of its Corresponding Source.  The information must
suffice to ensure that the continued functioning of the modified object
code is in no case prevented or interfered with solely because
modification has been made.

  If you convey an object code work under this section in, or with, or
specifically for use in, a User Product, and the conveying occurs as
part of a transaction in which the right of possession and use of the
User Product is transferred to the recipient in perpetuity or for a
fixed term (regardless of how the transaction is characterized), the
Corresponding Source conveyed under this section must be accompanied
by the Installation Information.  But this requirement does not apply
if neither you nor any third party retains the ability to install
modified object code on the User Product (for example, the work has
been installed in ROM).

  The requirement to provide Installation Information does not include a
requirement to continue to provide support service, warranty, or updates
for a work that has been modified or installed by the recipient, or for
the User Product in which it has been modified or installed.  Access to a
network may be denied when the modification itself materially and
adversely affects the operation of the network or violates the rules and
protocols for communication across the network.

  Corresponding Source conveyed, and Installation Information provided,
in accord with this section must be in a format that is publicly
documented (and with an implementation available to the public in
source code form), and must require no special password or key for
unpacking, reading or copying.

  7. Additional Terms.

  "Additional permissions" are terms that supplement the terms of this
License by making exceptions from one or more of its conditions.
Additional permissions that are applicable to the entire Program shall
be treated as though they were included in this License, to the extent
that they are valid under applicable law.  If additional permissions
apply only to part of the Program, that part may be used separately
under those permissions, but the entire Program remains governed by
this License without regard to the additional permissions.

  When you convey a copy of a covered work, you may at your option
remove any additional permissions from that copy, or from any part of
it.  (Additional permissions may be written to require their own
removal in certain cases when you modify the work.)  You may place
additional permissions on material, added by you to a covered work,
for which you have or can give appropriate copyright permission.

  Notwithstanding any other provision of this License, for material you
add to a covered work, you may (if authorized by the copyright holders of
that material) supplement the terms of this License with terms:

    a) Disclaiming warranty or limiting liability differently from the
    terms of sections 15 and 16 of this License; or

    b) Requiring preservation of specified reasonable legal notices or
    author attributions in that material or in the Appropriate Legal
    Notices displayed by works containing it; or

    c) Prohibiting misrepresentation of the origin of that material, or
    requiring that modified versions of such material be marked in
    reasonable ways as different from the original version; or

    d) Limiting the use for publicity purposes of names of licensors or
    authors of the material; or

    e) Declining to grant rights under trademark law for use of some
    trade names, trademarks, or service marks; or

    f) Requiring indemnification of licensors and authors of that
    material by anyone who conveys the material (or modified versions of
    it) with contractual assumptions of liability to the recipient, for
    any liability that these contractual assumptions directly impose on
    those licensors and authors.

  All other non-permissive additional terms are considered "further
restrictions" within the meaning of section 10.  If the Program as you
received it, or any part of it, contains a notice stating that it is
governed by this License along with a term that is a further
restriction, you may remove that term.  If a license document contains
a further restriction but permits relicensing or conveying under this
License, you may add to a covered work material governed by the terms
of that license document, provided that the further restriction does
not survive such relicensing or conveying.

  If you add terms to a covered work in accord with this section, you
must place, in the relevant source files, a statement of the
additional terms that apply to those files, or a notice indicating
where to find the applicable terms.

  Additional terms, permissive or non-permissive, may be stated in the
form of a separately written license, or stated as exceptions;
the above requirements apply either way.

  8. Termination.

  You may not propagate or modify a covered work except as expressly
provided under this License.  Any attempt otherwise to propagate or
modify it is void, and will automatically terminate your rights under
this License (including any patent licenses granted under the third
paragraph of section 11).

  However, if you cease all violation of this License, then your
license from a particular copyright holder is reinstated (a)
provisionally, unless and until the copyright holder explicitly and
finally terminates your license, and (b) permanently, if the copyright
holder fails to notify you of the violation by some reasonable means
prior to 60 days after the cessation.

  Moreover, your license from a particular copyright holder is
reinstated permanently if the copyright holder notifies you of the
violation by some reasonable means, this is the first time you have
received notice of violation of this License (for any work) from that
copyright holder, and you cure the violation prior to 30 days after
your receipt of the notice.

  Termination of your rights under this section does not terminate the
licenses of parties who have received copies or rights from you under
this License.  If your rights have been terminated and not permanently
reinstated, you do not qualify to receive new licenses for the same
material under section 10.

  9. Acceptance Not Required for Having Copies.

  You are not required to accept this License in order to receive or
run a copy of the Program.  Ancillary propagation of a covered work
occurring solely as a consequence of using peer-to-peer transmission
to receive a copy likewise does not require acceptance.  However,
nothing other than this License grants you permission to propagate or
modify any covered work.  These actions infringe copyright if you do
not accept this License.  Therefore, by modifying or propagating a
covered work, you indicate your acceptance of this License to do so.

  10. Automatic Licensing of Downstream Recipients.

  Each time you convey a covered work, the recipient automatically
receives a license from the original licensors, to run, modify and
propagate that work, subject to this License.  You are not responsible
for enforcing compliance by third parties with this License.

  An "entity transaction" is a transaction transferring control of an
organization, or substantially all assets of one, or subdividing an
organization, or merging organizations.  If propagation of a covered
work results from an entity transaction, each party to that
transaction who receives a copy of the work also receives whatever
licenses to the work the party's predecessor in interest had or could
give under the previous paragraph, plus a right to possession of the
Corresponding Source of the work from the predecessor in interest, if
the predecessor has it or can get it with reasonable efforts.

  You may not impose any further restrictions on the exercise of the
rights granted or affirmed under this License.  For example, you may
not impose a license fee, royalty, or other charge for exercise of
rights granted under this License, and you may not initiate litigation
(including a cross-claim or counterclaim in a lawsuit) alleging that
any patent claim is infringed by making, using, selling, offering for
sale, or importing the Program or any portion of it.

  11. Patents.

  A "contributor" is a copyright holder who authorizes use under this
License of the Program or a work on which the Program is based.  The
work thus licensed is called the contributor's "contributor version".

  A contributor's "essential patent claims" are all patent claims
owned or controlled by the contributor, whether already acquired or
hereafter acquired, that would be infringed by some manner, permitted
by this License, of making, using, or selling its contributor version,
but do not include claims that would be infringed only as a
consequence of further modification of the contributor version.  For
purposes of this definition, "control" includes the right to grant
patent sublicenses in a manner consistent with the requirements of
this License.

  Each contributor grants you a non-exclusive, worldwide, royalty-free
patent license under the contributor's essential patent claims, to
make, use, sell, offer for sale, import and otherwise run, modify and
propagate the contents of its contributor version.

  In the following three paragraphs, a "patent license" is any express
agreement or commitment, however denominated, not to enforce a patent
(such as an express permission to practice a patent or covenant not to
sue for patent infringement).  To "grant" such a patent license to a
party means to make such an agreement or commitment not to enforce a
patent against the party.

  If you convey a covered work, knowingly relying on a patent license,
and the Corresponding Source of the work is not available for anyone
to copy, free of charge and under the terms of this License, through a
publicly available network server or other readily accessible means,
then you must either (1) cause the Corresponding Source to be so
available, or (2) arrange to deprive yourself of the benefit of the
patent license for this particular work, or (3) arrange, in a manner
consistent with the requirements of this License, to extend the patent
license to downstream recipients.  "Knowingly relying" means you have
actual knowledge that, but for the patent license, your conveying the
covered work in a country, or your recipient's use of the covered work
in a country, would infringe one or more identifiable patents in that
country that you have reason to believe are valid.

  If, pursuant to or in connection with a single transaction or
arrangement, you convey, or propagate by procuring conveyance of, a
covered work, and grant a patent license to some of the parties
receiving the covered work authorizing them to use, propagate, modify
or convey a specific copy of the covered work, then the patent license
you grant is automatically extended to all recipients of the covered
work and works based on it.

  A patent license is "discriminatory" if it does not include within
the scope of its coverage, prohibits the exercise of, or is
conditioned on the non-exercise of one or more of the rights that are
specifically granted under this License.  You may not convey a covered
work if you are a party to an arrangement with a third party that is
in the business of distributing software, under which you make payment
to the third party based on the extent of your activity of conveying
the work, and under which the third party grants, to any of the
parties who would receive the covered work from you, a discriminatory
patent license (a) in connection with copies of the covered work
conveyed by you (or copies made from those copies), or (b) primarily
for and in connection with specific products or compilations that
contain the covered work, unless you entered into that arrangement,
or that patent license was granted, prior to 28 March 2007.

  Nothing in this License shall be construed as excluding or limiting
any implied license or other defenses to infringement that may
otherwise be available to you under applicable patent law.

  12. No Surrender of Others' Freedom.

  If conditions are imposed on you (whether by court order, agreement or
otherwise) that contradict the conditions of this License, they do not
excuse you from the conditions of this License.  If you cannot convey a
covered work so as to satisfy simultaneously your obligations under this
License and any other pertinent obligations, then as a consequence you may
not convey it at all.  For example, if you agree to terms that obligate you
to collect a royalty for further conveying from those to whom you convey
the Program, the only way you could satisfy both those terms and this
License would be to refrain entirely from conveying the Program.

  13. Use with the GNU Affero General Public License.

  Notwithstanding any other provision of this License, you have
permission to link or combine any covered work with a work licensed
under version 3 of the GNU Affero General Public License into a single
combined work, and to convey the resulting work.  The terms of this
License will continue to apply to the part which is the covered work,
but the special requirements of the GNU Affero General Public License,
section 13, concerning interaction through a network will apply to the
combination as such.

  14. Revised Versions of this License.

  The Free Software Foundation may publish revised and/or new versions of
the GNU General Public License from time to time.  Such new versions will
be similar in spirit to the present version, but may differ in detail to
address new problems or concerns.

  Each version is given a distinguishing version number.  If the
Program specifies that a certain numbered version of the GNU General
Public License "or any later version" applies to it, you have the
option of following the terms and conditions either of that numbered
version or of any later version published by the Free Software
Foundation.  If the Program does not specify a version number of the
GNU General Public License, you may choose any version ever published
by the Free Software Foundation.

  If the Program specifies that a proxy can decide which future
versions of the GNU General Public License can be used, that proxy's
public statement of acceptance of a version permanently authorizes you
to choose that version for the Program.

  Later license versions may give you additional or different
permissions.  However, no additional obligations are imposed on any
author or copyright holder as a result of your choosing to follow a
later version.

  15. Disclaimer of Warranty.

  THERE IS NO WARRANTY FOR THE PROGRAM, TO THE EXTENT PERMITTED BY
APPLICABLE LAW.  EXCEPT WHEN OTHERWISE STATED IN WRITING THE COPYRIGHT
HOLDERS AND/OR OTHER PARTIES PROVIDE THE PROGRAM "AS IS" WITHOUT WARRANTY
OF ANY KIND, EITHER EXPRESSED OR IMPLIED, INCLUDING, BUT NOT LIMITED TO,
THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
PURPOSE.  THE ENTIRE RISK AS TO THE QUALITY AND PERFORMANCE OF THE PROGRAM
IS WITH YOU.  SHOULD THE PROGRAM PROVE DEFECTIVE, YOU ASSUME THE COST OF
ALL NECESSARY SERVICING, REPAIR OR CORRECTION.

  16. Limitation of Liability.

  IN NO EVENT UNLESS REQUIRED BY APPLICABLE LAW OR AGREED TO IN WRITING
WILL ANY COPYRIGHT HOLDER, OR ANY OTHER PARTY WHO MODIFIES AND/OR CONVEYS
THE PROGRAM AS PERMITTED ABOVE, BE LIABLE TO YOU FOR DAMAGES, INCLUDING ANY
GENERAL, SPECIAL, INCIDENTAL OR CONSEQUENTIAL DAMAGES ARISING OUT OF THE
USE OR INABILITY TO USE THE PROGRAM (INCLUDING BUT NOT LIMITED TO LOSS OF
DATA OR DATA BEING RENDERED INACCURATE OR LOSSES SUSTAINED BY YOU OR THIRD
PARTIES OR A FAILURE OF THE PROGRAM TO OPERATE WITH ANY OTHER PROGRAMS),
EVEN IF SUCH HOLDER OR OTHER PARTY HAS BEEN ADVISED OF THE POSSIBILITY OF
SUCH DAMAGES.

  17. Interpretation of Sections 15 and 16.

  If the disclaimer of warranty and limitation of liability provided
above cannot be given local legal effect according to their terms,
reviewing courts shall apply local law that most closely approximates
an absolute waiver of all civil liability in connection with the
Program, unless a warranty or assumption of liability accompanies a
copy of the Program in return for a fee.

                     END OF TERMS AND CONDITIONS

            How to Apply These Terms to Your New Programs

  If you develop a new program, and you want it to be of the greatest
possible use to the public, the best way to achieve this is to make it
free software which everyone can redistribute and change under these terms.

  To do so, attach the following notices to the program.  It is safest
to attach them to the start of each source file to most effectively
state the exclusion of warranty; and each file should have at least
the "copyright" line and a pointer to where the full notice is found.

    <one line to give the program's name and a brief idea of what it does.>
    Copyright (C) <year>  <name of author>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.

Also add information on how to contact you by electronic and paper mail.

  If the program does terminal interaction, make it output a short
notice like this when it starts in an interactive mode:

    <program>  Copyright (C) <year>  <name of author>
    This program comes with ABSOLUTELY NO WARRANTY; for details type `show w'.
    This is free software, and you are welcome to redistribute it
    under certain conditions; type `show c' for details.

The hypothetical commands `show w' and `show c' should show the appropriate
parts of the General Public License.  Of course, your program's commands
might be different; for a GUI interface, you would use an "about box".

  You should also get your employer (if you work as a programmer) or school,
if any, to sign a "copyright disclaimer" for the program, if necessary.
For more information on this, and how to apply and follow the GNU GPL, see
<https://www.gnu.org/licenses/>.

  The GNU General Public License does not permit incorporating your program
into proprietary programs.  If your program is a subroutine library, you
may consider it more useful to permit linking proprietary applications with
the library.  If this is what you want to do, use the GNU Lesser General
Public License instead of this License.  But first, please read
<https://www.gnu.org/licenses/why-not-lgpl.html>.
"""

_DISCORD_PNG_B64 = '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'
_PWS32Z_AVATAR_B64 = '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E+NoPULBFXTrdzJMuWCLbX8Y5xF3N7ioPwMLgPTcbJ7z66iemK5dQAU9DuBzYwpduhqMl2WTghmJlF6Sv2Bu/h2KZJ0rh2pv6m+n+oEKnJDkjMHZL0g4TESl9AVQWxXIedh4IGgHyMAFGCbRipNQdxARoT+5eXFzbf5BhxLiKvLCtPj5g8LJU0gDj2oZfAzEXRs8S6HkxBPIS/ITbL7KnkIRQj+5XoLwxucOYlJctbjgDATzh7knUbgI5NUolnwlSSfncWtSxTt/lh0KCysrljQhjB4V17Dc1Ls8y37UxKmeJyg4R3MZoOyAgZf/AKJqFg27iBO9DiEV/PWqAmal1at+J3P7kf3SlEWl9HDZZ2w0Q4xTGb2v/FkgmyEqzRH/AFFCWv8AxjOGWCIbFN/8ZZvWoSldv/GVRS5f8aZ2rf8A6HtUVvn/APg9HSJ/xqh8MZf8aUg6jY/+LP/aAAwDAQACAAMAAAAQ4800888888848cs809ovTwcsYIs8w0888888888888888Mss8888884c8cgEYAs4cE4wDrtQk0c8888888888888888888888800M48sk4oEYcs8k0I0RJsIw8888888888888888s8888sc88b8MjQM888888ssEUU8A8888888888888888888888c888/j7J8888888888owwbo4888888888888888888888888Mn4ws88888888888880hw8888888888888888888880c850084088888888888IMXk888888888888888888888scs4888o88888888088oQk0M888888888888888888888YRwp088808888884888sEwUI888888888888888888888goMA88o888k08U44cEw84A88808888888888888888888ssk488g848gwg438QYcws8Q8Yw88888888888888888888Jc3840o84EbfE8o0nPE8Y80A8888888888888888888880IAco0Q8soD33jsY80Qcsw5E08888888888888888888YUv8U8Uc88swcFLkMY3EMUkU88888888888888888ww4084UQXI0888088BYzlwMg808Ac0888888888888888c8888MpMIIs88o088FQAkIME50TzE888888888888888888808sE8cY0U8c888k4AwwMsrIoUU8888888888888888888888cU8s088888sE8k40AkjAAU888888888888888888A80808ssMEc88888wbZ8AsE/cc888888888888888888jvL/Qw8888s088888I0DswsMB8888888888888888888sfA1QjzvU08oA4888YAssD3XsZ88888888888888888888sM/EvbrDbUsw4c88skMzcvs0IkIw8888888888888888888884bHDbc8Uo8884UZFHLkgYo4YYkP088885vs4888888888QXLhEAYk8Ic88QfH0/TrA48sMk4cw888YnsU88888888888cs840sU8888YwErDwhH88888MYok888888888888804ws/oY8YUA888Ugk07QoI488888888oAU08w8888880gEYQUYs88AMU0U4880z3XUI8888888888soEQowdg84wE84MUMM888M88c4j8sgEnT8c888888888888scAcQ8ww44U888888888888MAU8U0EM88888888888888888scJIEM8888888888888888M8888888888888888888888884Y88888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888488888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888w88888888888888888888888888888888888888888888cc8888888888888888888888888888888888888888888888888888888888888888888888888888888888888//xAAcEQACAgIDAAAAAAAAAAAAAAAB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'

def _load_embedded_image(b64_str, size):
    if not PIL_AVAILABLE:
        return None
    try:
        import base64 as _b64, io as _io
        data = _b64.b64decode(b64_str)
        img = Image.open(_io.BytesIO(data)).convert('RGBA').resize((size, size), Image.LANCZOS)
        return ImageTk.PhotoImage(img)
    except Exception:
        return None

try:
    import win32gui
    import win32process
    import win32con
    import win32api
    import psutil
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False

_BASE_DIR = (
    os.path.dirname(sys.executable)
    if getattr(sys, "frozen", False)
    else os.path.dirname(os.path.abspath(__file__))
)
CONFIG_FILE = os.path.join(_BASE_DIR, "config.json")

BG_BASE        = "#0e0f11"
BG_SIDEBAR     = "#13151a"
BG_CARD        = "#1a1d25"
BG_ITEM        = "#20242f"
BG_HOVER       = "#252936"
BG_ACTIVE_NAV  = "#1e2235"
BORDER         = "#2a2d3a"
BORDER_ITEM    = "#30344a"
ACCENT         = "#5865f2"
ACCENT_DIM     = "#1a1e3a"
ACCENT_HOVER   = "#4752c4"
TEXT_PRIMARY   = "#e8eaf0"
TEXT_MUTED     = "#9199b0"
TEXT_DIM       = "#6b7290"
TEXT_FAINT     = "#454a62"
TEXT_FAINTEST  = "#2e3248"
RED            = "#f04747"
RED_BG         = "#1f1215"
RED_HOVER      = "#2a1820"
WARN           = "#faa61a"
WARN_BG        = "#1e1a0f"
DISCORD_COLOR  = "#5865F2"
PURPLE         = "#a855f7"
CYAN           = "#06b6d4"
ORANGE         = "#f97316"
GOLD           = "#faa61a"

_BIOMES_REMOTE_URL = "https://raw.githubusercontent.com/cresqnt-sys/MultiScope/refs/heads/main/assets/biomes.json"

def _load_biome_data():
    """Load biome data from remote URL, then local biomes.json, then hardcoded fallback."""
    fallback = {
        "WINDY":      {"emoji": "🌀", "color": "0xFFFFFF", "thumbnail_url": "https://maxstellar.github.io/biome_thumb/WINDY.png"},
        "RAINY":      {"emoji": "🌧️", "color": "0x55925F", "thumbnail_url": "https://maxstellar.github.io/biome_thumb/RAINY.png"},
        "SNOWY":      {"emoji": "❄️",  "color": "0xFFFFFF", "thumbnail_url": "https://maxstellar.github.io/biome_thumb/SNOWY.png"},
        "SAND STORM": {"emoji": "🏜️", "color": "0xFFA500", "thumbnail_url": "https://maxstellar.github.io/biome_thumb/SAND%20STORM.png"},
        "HELL":       {"emoji": "🔥",  "color": "0xFB4F29", "thumbnail_url": "https://maxstellar.github.io/biome_thumb/HELL.png"},
        "STARFALL":   {"emoji": "🌠",  "color": "0xFFFFFF", "thumbnail_url": "https://maxstellar.github.io/biome_thumb/STARFALL.png"},
        "CORRUPTION": {"emoji": "🌑",  "color": "0x800080", "thumbnail_url": "https://maxstellar.github.io/biome_thumb/CORRUPTION.png"},
        "NULL":       {"emoji": "🌫️", "color": "0x808080", "thumbnail_url": "https://maxstellar.github.io/biome_thumb/NULL.png"},
        "GLITCHED":   {"emoji": "⚠️",  "color": "0xFFFF00", "thumbnail_url": "https://i.postimg.cc/mDzwFfX1/GLITCHED.png", "force_notify": True, "ping_everyone": True},
        "DREAMSPACE": {"emoji": "💤",  "color": "0xFF00FF", "thumbnail_url": "https://maxstellar.github.io/biome_thumb/DREAMSPACE.png", "force_notify": True, "ping_everyone": True},
        "CYBERSPACE": {"emoji": "🌐",  "color": "0x00FFFF", "thumbnail_url": "https://raw.githubusercontent.com/cresqnt-sys/MultiScope/refs/heads/main/assets/cyberspace.png", "force_notify": True, "ping_everyone": True},
        "SINGULARITY": {"emoji": "🌌", "color": "0x9400D3", "thumbnail_url": "https://raw.githubusercontent.com/pws32z/MultiFMacro/main/assets/SINGULARITY.png", "force_notify": True, "ping_everyone": True},
        "EGGLAND":    {"emoji": "🥚",  "color": "0xFFD700", "thumbnail_url": "https://raw.githubusercontent.com/xVapure/Noteab-Macro/refs/heads/main/images/EGGLAND.png"},
        "HEAVEN":     {"emoji": "☁️",  "color": "0xADD8E6", "thumbnail_url": "https://cresqnt.com/api/images/HEAVEN.png"},
        "NORMAL":     {"emoji": "🌳",  "color": "0x00FF00", "thumbnail_url": "", "never_notify": True},
    }
    data = fallback.copy()

    _local = os.path.join(os.path.dirname(os.path.abspath(__file__)), "biomes.json")
    if os.path.exists(_local):
        try:
            with open(_local, "r", encoding="utf-8") as _f:
                _local_data = json.load(_f)
            for k, v in _local_data.items():
                if not k.startswith("_"):
                    data[k] = v
        except Exception:
            pass

    try:
        _req = urllib.request.Request(_BIOMES_REMOTE_URL,
                                      headers={"User-Agent": "MultiFInstance/1.0"})
        with urllib.request.urlopen(_req, timeout=6) as _r:
            _remote = json.loads(_r.read())
        for k, v in _remote.items():
            if not k.startswith("_"):
                data[k] = v
    except Exception:
        pass

    for _bname, _binfo in data.items():
        _c = _binfo.get("color", "0xFFFFFF")
        if isinstance(_c, int):
            _binfo["color"] = f"0x{_c:06X}"
        elif isinstance(_c, str) and not _c.startswith("0x"):
            try:
                _binfo["color"] = f"0x{int(_c):06X}"
            except (ValueError, TypeError):
                _binfo["color"] = "0xFFFFFF"
        if "emoji" not in _binfo or not _binfo["emoji"]:
            _binfo["emoji"] = "🌍"
        if "thumbnail_url" not in _binfo:
            _binfo["thumbnail_url"] = ""
    return data

def _load_biome_data_fast():
    """Load only from fallback + local biomes.json (no network, instant)."""
    fallback = {
        "WINDY":      {"emoji": "🌀", "color": "0xFFFFFF", "thumbnail_url": "https://maxstellar.github.io/biome_thumb/WINDY.png"},
        "RAINY":      {"emoji": "🌧️", "color": "0x55925F", "thumbnail_url": "https://maxstellar.github.io/biome_thumb/RAINY.png"},
        "SNOWY":      {"emoji": "❄️",  "color": "0xFFFFFF", "thumbnail_url": "https://maxstellar.github.io/biome_thumb/SNOWY.png"},
        "SAND STORM": {"emoji": "🏜️", "color": "0xFFA500", "thumbnail_url": "https://maxstellar.github.io/biome_thumb/SAND%20STORM.png"},
        "HELL":       {"emoji": "🔥",  "color": "0xFB4F29", "thumbnail_url": "https://maxstellar.github.io/biome_thumb/HELL.png"},
        "STARFALL":   {"emoji": "🌠",  "color": "0xFFFFFF", "thumbnail_url": "https://maxstellar.github.io/biome_thumb/STARFALL.png"},
        "CORRUPTION": {"emoji": "🌑",  "color": "0x800080", "thumbnail_url": "https://maxstellar.github.io/biome_thumb/CORRUPTION.png"},
        "NULL":       {"emoji": "🌫️", "color": "0x808080", "thumbnail_url": "https://maxstellar.github.io/biome_thumb/NULL.png"},
        "GLITCHED":   {"emoji": "⚠️",  "color": "0xFFFF00", "thumbnail_url": "https://i.postimg.cc/mDzwFfX1/GLITCHED.png", "force_notify": True, "ping_everyone": True},
        "DREAMSPACE": {"emoji": "💤",  "color": "0xFF00FF", "thumbnail_url": "https://maxstellar.github.io/biome_thumb/DREAMSPACE.png", "force_notify": True, "ping_everyone": True},
        "CYBERSPACE": {"emoji": "🌐",  "color": "0x00FFFF", "thumbnail_url": "https://raw.githubusercontent.com/cresqnt-sys/MultiScope/refs/heads/main/assets/cyberspace.png", "force_notify": True, "ping_everyone": True},
        "SINGULARITY": {"emoji": "🌌", "color": "0x9400D3", "thumbnail_url": "https://raw.githubusercontent.com/pws32z/MultiFMacro/main/assets/SINGULARITY.png", "force_notify": True, "ping_everyone": True},
        "EGGLAND":    {"emoji": "🥚",  "color": "0xFFD700", "thumbnail_url": "https://raw.githubusercontent.com/xVapure/Noteab-Macro/refs/heads/main/images/EGGLAND.png"},
        "HEAVEN":     {"emoji": "☁️",  "color": "0xADD8E6", "thumbnail_url": "https://cresqnt.com/api/images/HEAVEN.png"},
        "NORMAL":     {"emoji": "🌳",  "color": "0x00FF00", "thumbnail_url": "", "never_notify": True},
    }
    data = fallback.copy()
    _local = os.path.join(os.path.dirname(os.path.abspath(__file__)), "biomes.json")
    if os.path.exists(_local):
        try:
            with open(_local, "r", encoding="utf-8") as _f:
                _local_data = json.load(_f)
            for k, v in _local_data.items():
                if not k.startswith("_"):
                    data[k] = v
        except Exception:
            pass
    for _bname, _binfo in data.items():
        _c = _binfo.get("color", "0xFFFFFF")
        if isinstance(_c, int):
            _binfo["color"] = f"0x{_c:06X}"
        elif isinstance(_c, str) and not _c.startswith("0x"):
            try:
                _binfo["color"] = f"0x{int(_c):06X}"
            except (ValueError, TypeError):
                _binfo["color"] = "0xFFFFFF"
        if "emoji" not in _binfo or not _binfo["emoji"]:
            _binfo["emoji"] = "🌍"
        if "thumbnail_url" not in _binfo:
            _binfo["thumbnail_url"] = ""
    return data

BIOME_DATA = _load_biome_data_fast()

def _refresh_biome_data_bg():
    """Fetch remote biomes.json in background and merge into BIOME_DATA."""
    try:
        _req = urllib.request.Request(_BIOMES_REMOTE_URL,
                                      headers={"User-Agent": "MultiFInstance/1.0"})
        with urllib.request.urlopen(_req, timeout=6) as _r:
            _remote = json.loads(_r.read())
        for k, v in _remote.items():
            if not k.startswith("_"):
                BIOME_DATA[k] = v
    except Exception:
        pass

threading.Thread(target=_refresh_biome_data_bg, daemon=True).start()

def _build_biomes_list():
    out = []
    for name, info in BIOME_DATA.items():
        if name == "NORMAL":
            continue
        try:
            color_int = int(info.get("color", "0xFFFFFF").replace("0x", ""), 16)
            color_hex = f"#{color_int:06X}"
        except Exception:
            color_hex = "#FFFFFF"
        force = info.get("force_notify", False) and info.get("ping_everyone", False)
        alias = [name.lower()]
        out.append((name, color_hex, force, alias))
    return out

BIOMES = _build_biomes_list()

BIOME_IMAGES = {name: info.get("thumbnail_url", "") for name, info in BIOME_DATA.items()}

VERSION = "1"

AURA_DATA = [
    ("Memory, The Fallen",         "Oblivion Potion"),
    ("Oblivion: The truth seeker", "Oblivion Potion"),
    ("Exotic",                     "1/99,999"),
    ("Diaboli: Void",              "1/100,400"),
    ("Undead: Devil",              "1/120,000"),
    ("Comet",                      "1/120,000"),
    ("Jade",                       "1/125,000"),
    ("Spectre",                    "1/140,000"),
    ("Jazz",                       "1/160,000"),
    ("Aether",                     "1/180,000"),
    ("Bounded",                    "1/200,000"),
    ("Celestial",                  "1/350,000"),
    ("Kyawthuite",                 "1/850,000"),
    ("Arcane",                     "1/1,000,000"),
    ("Magnetic: Reverse Polarity", "1/1,024,000"),
    ("Undefined",                  "1/1,111,000"),
    ("Rage: Brawler",              "1/1,280,000"),
    ("Astral",                     "1/1,336,000"),
    ("Gravitational",              "1/2,000,000"),
    ("Bounded: Unbound",           "1/2,000,000"),
    ("Virtual",                    "1/2,500,000"),
    ("Savior",                     "1/3,200,000"),
    ("Poseidon",                   "1/4,000,000"),
    ("Aquatic: Flame",             "1/4,000,000"),
    ("Zeus",                       "1/4,500,000"),
    ("Lunar: Full Moon",           "1/5,000,000"),
    ("Solar: Solstice",            "1/5,000,000"),
    ("Galaxy",                     "1/5,000,000"),
    ("Twilight",                   "1/6,000,000"),
    ("Origin",                     "1/6,500,000"),
    ("Hades",                      "1/6,666,666"),
    ("Celestial: Divine",          "1/7,000,000"),
    ("Hyper-volt",                 "1/7,500,000"),
    ("Nihility",                   "1/9,000,000"),
    ("Starscourge",                "1/10,000,000"),
    ("Sailor",                     "1/12,000,000"),
    ("Glitch",                     "1/12,000,000"),
    ("Stormal: Hurricane",         "1/13,500,000"),
    ("Sirius",                     "1/14,000,000"),
    ("Arcane: Legacy",             "1/15,000,000"),
    ("Chromatic",                  "1/20,000,000"),
    ("Aviator",                    "1/24,000,000"),
    ("Arcane: Dark",               "1/30,000,000"),
    ("Ethereal",                   "1/35,000,000"),
    ("Overseer",                   "1/45,000,000"),
    ("Exotic: Apex",               "1/49,999,500"),
    ("Matrix",                     "1/50,000,000"),
    ("Twilight: Iridescent Memory","1/60,000,000"),
    ("Sailor: Flying Dutchman",    "1/80,000,000"),
    ("Chromatic: Genesis",         "1/99,999,999"),
    ("Spectraflow",                "1/100,000,000"),
    ("Starscourge: Radiant",       "1/100,000,000"),
    ("Overture",                   "1/150,000,000"),
    ("Symphony",                   "1/175,000,000"),
    ("Felled",                     "1/180,000,000"),
    ("Twilight: Withering Grace",  "1/180,000,000"),
    ("Impeached",                  "1/200,000,000"),
    ("Lumenpool",                  "1/220,000,000"),
    ("Oppression",                 "1/220,000,000"),
    ("Hyper-Volt: Ever-Storm",     "1/225,000,000"),
    ("Shard Surfer",               "1/225,000,000"),
    ("Archangel",                  "1/250,000,000"),
    ("Astral: Zodiac",             "1/267,200,000"),
    ("Prophecy",                   "1/275,649,430"),
    ("Exotic: Void",               "1/299,999,999"),
    ("Bloodlust",                  "1/300,000,000"),
    ("Overture: History",          "1/300,000,000"),
    ("Maelstrom",                  "1/309,999,999"),
    ("Perpetual",                  "1/315,000,000"),
    ("Orchestra",                  "1/336,870,912"),
    ("Atlas",                      "1/360,000,000"),
    ("Flora: Evergreen",           "1/370,073,730"),
    ("Chillsear",                  "1/375,000,000"),
    ("Abyssal Hunter",             "1/400,000,000"),
    ("Gargantua",                  "1/430,000,000"),
    ("Apostolos",                  "1/444,000,000"),
    ("Unknown",                    "1/444,444,444"),
    ("Kyawthuite: Remembrance",    "1/450,000,000"),
    ("Ruins",                      "1/500,000,000"),
    ("Matrix: Overdrive",          "1/503,000,000"),
    ("Elude",                      "1/555,555,555"),
    ("Sophyra",                    "1/570,000,000"),
    ("Matrix: Reality",            "1/601,020,102"),
    ("Prologue",                   "1/666,616,111"),
    ("Pythios",                    "1/666,666,666"),
    ("Aegis",                      "1/825,000,000"),
    ("dreamscape",                 "1/850,000,000"),
    ("Ruins: Withered",            "1/800,000,000"),
    ("Ascendant",                  "1/935,000,000"),
    ("Nyctophobia",                "1/1,011,111,010"),
    ("Pixelation",                 "1/1,073,741,824"),
    ("Luminosity",                 "1/1,200,000,000"),
    ("Leviathan",                  "1/1,730,400,000"),
    ("Breakthrough",               "1/1,999,999,999"),
    ("Equinox",                    "1/2,500,000,000"),
    ("Monarch",                    "1/3,000,000,000"),
    ("Sovereign",                  "1/750,000,000"),
    ("Astraios",                   "1/1,750,000,000"),
    ("Virtual:Memory",             "1/232,232,232"),
    ("Point:Zero",                 "1/120,000,000"),
    ("Projection",                 "1/197,000,000"),
]
AURA_LOOKUP = {a[0].lower(): a for a in AURA_DATA}

def fr(parent, bg=BG_BASE, **kw):
    return tk.Frame(parent, bg=bg, bd=0, highlightthickness=0, **kw)

def lbl(parent, text="", fg=TEXT_PRIMARY, bg=BG_BASE, font=("Segoe UI", 10), **kw):
    return tk.Label(parent, text=text, fg=fg, bg=bg, font=font, **kw)

def card(parent, **kw):
    return tk.Frame(parent, bg=BG_CARD, bd=0,
                    highlightthickness=1, highlightbackground=BORDER, **kw)

def sep(parent, bg=BORDER):
    return tk.Frame(parent, bg=bg, height=1, bd=0, highlightthickness=0)

def dot(parent, color, bg, size=7):
    c = tk.Canvas(parent, width=size + 4, height=size + 4,
                  bg=bg, highlightthickness=0, bd=0)
    m = 2
    c.create_oval(m, m, m + size, m + size, fill=color, outline="")
    return c

def styled_entry(parent, textvariable=None, width=None, **kw):
    opts = dict(bg=BG_ITEM, fg=TEXT_MUTED, insertbackground=ACCENT,
                relief="flat", font=("Segoe UI", 9),
                highlightthickness=1, highlightbackground=BORDER_ITEM,
                highlightcolor=ACCENT,
                selectbackground=ACCENT_DIM, selectforeground=TEXT_PRIMARY)
    if textvariable:
        opts["textvariable"] = textvariable
    if width:
        opts["width"] = width
    opts.update(kw)
    e = tk.Entry(parent, **opts)
    e.bind("<FocusIn>",  lambda ev: _anim_border(e, BORDER_ITEM, ACCENT, steps=8, delay=10))
    e.bind("<FocusOut>", lambda ev: _anim_border(e, ACCENT, BORDER_ITEM, steps=8, delay=10))
    return e

def styled_check(parent, variable, **kw):
    """Checkbutton with animated hover — accent glow on hover, smooth fg transition."""
    cb = tk.Checkbutton(parent, variable=variable,
                        bg=kw.pop("bg", BG_CARD),
                        fg=kw.pop("fg", TEXT_MUTED),
                        selectcolor=kw.pop("selectcolor", ACCENT_DIM),
                        activebackground=kw.pop("activebackground", BG_HOVER),
                        activeforeground=kw.pop("activeforeground", ACCENT),
                        highlightthickness=0, cursor="hand2",
                        relief="flat", bd=0, **kw)
    _base_bg = cb.cget("bg")
    cb.bind("<Enter>", lambda e: (cb.config(bg=BG_HOVER),
                                  _anim_fg(cb, TEXT_MUTED, ACCENT, steps=5, delay=8)))
    cb.bind("<Leave>", lambda e: (cb.config(bg=_base_bg),
                                  _anim_fg(cb, ACCENT, TEXT_MUTED, steps=5, delay=8)))
    return cb


_ANIM_ROOT = None

def _lerp_hex(c1, c2, t):
    r = int(int(c1[1:3],16) + (int(c2[1:3],16) - int(c1[1:3],16)) * t)
    g = int(int(c1[3:5],16) + (int(c2[3:5],16) - int(c1[3:5],16)) * t)
    b = int(int(c1[5:7],16) + (int(c2[5:7],16) - int(c1[5:7],16)) * t)
    return f"#{r:02x}{g:02x}{b:02x}"

def _anim_bg(widget, from_c, to_c, steps=8, delay=10, _step=0):
    if _step > steps or not _ANIM_ROOT:
        return
    col = _lerp_hex(from_c, to_c, _step / steps)
    try:
        widget.config(bg=col)
    except Exception:
        return
    _ANIM_ROOT.after(delay, lambda: _anim_bg(widget, from_c, to_c, steps, delay, _step+1))

def _anim_fg(widget, from_c, to_c, steps=8, delay=10, _step=0):
    if _step > steps or not _ANIM_ROOT:
        return
    col = _lerp_hex(from_c, to_c, _step / steps)
    try:
        widget.config(fg=col)
    except Exception:
        return
    _ANIM_ROOT.after(delay, lambda: _anim_fg(widget, from_c, to_c, steps, delay, _step+1))

def _anim_border(widget, from_c, to_c, steps=8, delay=10, _step=0):
    if _step > steps or not _ANIM_ROOT:
        return
    col = _lerp_hex(from_c, to_c, _step / steps)
    try:
        widget.config(highlightbackground=col)
    except Exception:
        return
    _ANIM_ROOT.after(delay, lambda: _anim_border(widget, from_c, to_c, steps, delay, _step+1))

def _ripple_btn(widget, steps=10, delay=18, _step=0):
    """Pulse a button's bg outward then back — visible press ripple."""
    if not _ANIM_ROOT:
        return
    PEAK = "#7983f5"
    if _step <= steps // 2:
        t   = _step / (steps // 2)
        col = _lerp_hex(ACCENT_HOVER, PEAK, t)
    else:
        t   = (_step - steps // 2) / (steps // 2)
        col = _lerp_hex(PEAK, ACCENT, t)
    try:
        widget.config(bg=col)
    except Exception:
        return
    if _step < steps:
        _ANIM_ROOT.after(delay, lambda: _ripple_btn(widget, steps, delay, _step + 1))

def _anim_arrow(arrow_cv, expanding, _step=0, _total=8, _delay=18):
    """Rotate a Canvas arrow from 0deg (pointing right) to 90deg (pointing down)."""
    if not _ANIM_ROOT:
        return
    import math
    start_angle = 0 if expanding else 90
    end_angle   = 90 if expanding else 0
    t = _step / _total
    ease = t * t * (3 - 2 * t)
    angle_deg = start_angle + (end_angle - start_angle) * ease
    angle = math.radians(angle_deg)
    cx, cy, size = 8, 8, 5
    pts = [
        (cx + size * math.cos(a + angle), cy + size * math.sin(a + angle))
        for a in (math.radians(-30), math.radians(210), math.radians(90))
    ]
    flat = [v for pt in pts for v in pt]
    col = ACCENT if expanding else TEXT_FAINT
    try:
        arrow_cv.delete("arr")
        arrow_cv.create_polygon(flat, fill=col, outline="", tags="arr")
    except Exception:
        return
    if _step < _total:
        _ANIM_ROOT.after(_delay, lambda: _anim_arrow(arrow_cv, expanding, _step+1, _total, _delay))

def make_arrow_canvas(parent, bg=BG_CARD):
    """Create a 16x16 Canvas triangle arrow (initially pointing right like ▶)."""
    import math
    cv = tk.Canvas(parent, width=16, height=16, bg=bg,
                   highlightthickness=0, bd=0, cursor="hand2")
    cx, cy, size = 8, 8, 5
    pts = [
        (cx + size * math.cos(a), cy + size * math.sin(a))
        for a in (math.radians(-30), math.radians(210), math.radians(90))
    ]
    flat = [v for pt in pts for v in pt]
    cv.create_polygon(flat, fill=TEXT_FAINT, outline="", tags="arr")
    return cv

def _anim_glow(widget, from_c, to_c, steps=10, delay=12, _step=0):
    """Animate highlightbackground (border glow)."""
    if _step > steps or not _ANIM_ROOT:
        return
    col = _lerp_hex(from_c, to_c, _step / steps)
    try:
        widget.config(highlightbackground=col)
    except Exception:
        return
    _ANIM_ROOT.after(delay, lambda: _anim_glow(widget, from_c, to_c, steps, delay, _step + 1))

def _pulse_glow(widget, base_c, peak_c, steps=8, delay=10, _step=0):
    """Pulse border glow out then back — for press effect."""
    if not _ANIM_ROOT:
        return
    half = steps // 2
    if _step <= half:
        col = _lerp_hex(base_c, peak_c, _step / half)
    else:
        col = _lerp_hex(peak_c, base_c, (_step - half) / half)
    try:
        widget.config(highlightbackground=col)
    except Exception:
        return
    if _step < steps:
        _ANIM_ROOT.after(delay, lambda: _pulse_glow(widget, base_c, peak_c, steps, delay, _step + 1))

def icon_btn(parent, text, fg=TEXT_DIM, bg=BG_ITEM, font=("Segoe UI", 9),
             command=None, padx=10, pady=5, hover_fg=ACCENT, hover_bg=None, **kw):
    _hbg = hover_bg or BG_HOVER
    b = tk.Button(parent, text=text, fg=fg, bg=bg, font=font,
                  relief="flat", bd=0, cursor="hand2",
                  activeforeground=hover_fg, activebackground=_hbg,
                  highlightthickness=1, highlightbackground=BORDER,
                  command=command, padx=padx, pady=pady, **kw)
    def _enter(e):
        _anim_bg(b, bg, _hbg, steps=7, delay=7)
        _anim_fg(b, fg, hover_fg, steps=7, delay=7)
        _anim_glow(b, BORDER, ACCENT, steps=8, delay=8)
    def _leave(e):
        _anim_bg(b, _hbg, bg, steps=7, delay=7)
        _anim_fg(b, hover_fg, fg, steps=7, delay=7)
        _anim_glow(b, ACCENT, BORDER, steps=8, delay=8)
    def _press(e):
        _anim_bg(b, _hbg, ACCENT_DIM, steps=3, delay=5)
        _pulse_glow(b, ACCENT, "#8891ff", steps=6, delay=6)
    def _release(e):
        _anim_bg(b, ACCENT_DIM, _hbg, steps=4, delay=6)
    b.bind("<Enter>", _enter)
    b.bind("<Leave>", _leave)
    b.bind("<ButtonPress-1>", _press)
    b.bind("<ButtonRelease-1>", _release)
    return b

def accent_btn(parent, text, command=None, padx=14, pady=6, **kw):
    """Canvas-wrapped accent button with fully visible animated border glow."""
    import math
    _font = kw.pop("font", ("Segoe UI", 9, "bold"))

    wrapper = tk.Frame(parent, bg=ACCENT, bd=0, highlightthickness=0)
    inner_pad = tk.Frame(wrapper, bg=ACCENT, bd=2, highlightthickness=0)
    inner_pad.pack(fill="both", expand=True, padx=1, pady=1)

    b = tk.Button(inner_pad, text=text, fg="#ffffff", bg=ACCENT,
                  font=_font,
                  relief="flat", bd=0, cursor="hand2",
                  activebackground=ACCENT_HOVER, activeforeground="#ffffff",
                  highlightthickness=0,
                  command=command, padx=padx, pady=pady, **kw)
    b.pack(fill="both", expand=True)

    _ring = [ACCENT]

    def _set_ring(col):
        _ring[0] = col
        try:
            wrapper.config(bg=col)
            inner_pad.config(bg=col)
        except Exception:
            pass

    def _anim_ring(from_c, to_c, steps=8, delay=6, _step=0):
        if _step > steps or not _ANIM_ROOT:
            return
        col = _lerp_hex(from_c, to_c, _step / steps)
        _set_ring(col)
        _ANIM_ROOT.after(delay, lambda: _anim_ring(from_c, to_c, steps, delay, _step+1))

    def _enter(e):
        _anim_bg(b, ACCENT, ACCENT_HOVER, steps=6, delay=6)
        _anim_ring(ACCENT, "#a0a8ff", steps=8, delay=6)
    def _leave(e):
        _anim_bg(b, ACCENT_HOVER, ACCENT, steps=6, delay=6)
        _anim_ring("#a0a8ff", ACCENT, steps=8, delay=6)
    def _press(e):
        _anim_bg(b, ACCENT_HOVER, "#3b3fd4", steps=3, delay=4)
        _anim_ring("#a0a8ff", "#ffffff", steps=4, delay=4)
        try:
            sz = int(_font[1]) if len(_font) > 1 else 9
            b.config(font=(_font[0], sz + 1, _font[2] if len(_font) > 2 else "bold"))
        except Exception: pass
    def _release(e):
        _anim_bg(b, "#3b3fd4", ACCENT_HOVER, steps=4, delay=5)
        _anim_ring("#ffffff", ACCENT, steps=5, delay=5)
        if _ANIM_ROOT: _ANIM_ROOT.after(80, lambda: b.config(font=_font))

    for w in [wrapper, inner_pad, b]:
        w.bind("<Enter>", _enter)
        w.bind("<Leave>", _leave)
        w.bind("<ButtonPress-1>", _press)
        w.bind("<ButtonRelease-1>", _release)

    wrapper._btn = b
    return wrapper

def red_btn(parent, text, command=None, padx=12, pady=5, **kw):
    b = tk.Button(parent, text=text, fg=RED, bg=RED_BG,
                  font=("Segoe UI", 9, "bold"),
                  relief="flat", bd=0, cursor="hand2",
                  activebackground=RED_HOVER, activeforeground=RED,
                  highlightthickness=1, highlightbackground="#2a1010",
                  command=command, padx=padx, pady=pady, **kw)
    def _enter(e):
        _anim_bg(b, RED_BG, RED_HOVER, steps=6, delay=7)
        _anim_glow(b, "#2a1010", RED, steps=8, delay=7)
    def _leave(e):
        _anim_bg(b, RED_HOVER, RED_BG, steps=6, delay=7)
        _anim_glow(b, RED, "#2a1010", steps=8, delay=7)
    def _press(e):
        _anim_bg(b, RED_HOVER, "#3d1010", steps=3, delay=5)
        _pulse_glow(b, RED, "#ff8888", steps=6, delay=5)
    def _release(e):
        _anim_bg(b, "#3d1010", RED_HOVER, steps=3, delay=5)
    b.bind("<Enter>", _enter)
    b.bind("<Leave>", _leave)
    b.bind("<ButtonPress-1>", _press)
    b.bind("<ButtonRelease-1>", _release)
    return b

def green_btn(parent, text, command=None, padx=12, pady=5, **kw):
    b = tk.Button(parent, text=text, fg="#ffffff", bg="#22c55e",
                  font=("Segoe UI", 9, "bold"),
                  relief="flat", bd=0, cursor="hand2",
                  activebackground="#16a34a", activeforeground="#ffffff",
                  highlightthickness=1, highlightbackground="#0f4a20",
                  command=command, padx=padx, pady=pady, **kw)
    def _enter(e):
        _anim_bg(b, "#22c55e", "#16a34a", steps=6, delay=7)
        _anim_glow(b, "#0f4a20", "#22c55e", steps=8, delay=7)
    def _leave(e):
        _anim_bg(b, "#16a34a", "#22c55e", steps=6, delay=7)
        _anim_glow(b, "#22c55e", "#0f4a20", steps=8, delay=7)
    def _press(e):
        _anim_bg(b, "#16a34a", "#0f7a36", steps=3, delay=5)
        _pulse_glow(b, "#22c55e", "#86efac", steps=6, delay=5)
    def _release(e): _anim_bg(b, "#0f7a36", "#16a34a", steps=3, delay=5)
    b.bind("<Enter>", _enter)
    b.bind("<Leave>", _leave)
    b.bind("<ButtonPress-1>", _press)
    b.bind("<ButtonRelease-1>", _release)
    return b


    """Card with animated border glow on hover."""
    f = tk.Frame(parent, bg=BG_CARD, bd=0,
                 highlightthickness=1, highlightbackground=BORDER, **kw)
    f.bind("<Enter>", lambda e: _anim_border(f, BORDER, "#3a3f5c", steps=8, delay=10))
    f.bind("<Leave>", lambda e: _anim_border(f, "#3a3f5c", BORDER, steps=8, delay=10))
    return f

class ScrollFrame(tk.Frame):
    def __init__(self, parent, bg=BG_BASE, **kw):
        super().__init__(parent, bg=bg, **kw)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.inner = tk.Frame(self.canvas, bg=bg)
        self._win_id = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", self._on_inner_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self._bind_scroll(self.canvas)
        self.inner.bind("<Enter>", self._rebind_all, add="+")
        self.canvas.bind("<Enter>",  self._rebind_all, add="+")

    def _on_inner_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self._win_id, width=event.width)

    def _bind_scroll(self, w):
        w.bind("<MouseWheel>", self._scroll, add="+")
        w.bind("<Button-4>",   self._scroll_up,   add="+")
        w.bind("<Button-5>",   self._scroll_down, add="+")

    def _rebind_all(self, event=None):
        """Recursively bind mouse-wheel on every widget inside inner so the
        scroll works no matter which child the cursor is hovering over."""
        def _walk(w):
            self._bind_scroll(w)
            for child in w.winfo_children():
                _walk(child)
        _walk(self.inner)

    def _scroll(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _scroll_up(self, event):
        self.canvas.yview_scroll(-1, "units")

    def _scroll_down(self, event):
        self.canvas.yview_scroll(1, "units")

    def bind_mousewheel(self, widget):
        """Bind an additional widget (e.g. a Listbox inside inner) to this scroll."""
        self._bind_scroll(widget)


LOG_READ_SIZE        = 1 * 1024 * 1024
LOG_TAIL_READ_BYTES  = 2 * 1024 * 1024
LOG_UPDATE_INTERVAL  = 8

DEFAULT_WEBHOOK_RATE_LIMIT = 1.0

_ROBLOX_LOG_DIRS = [
    os.path.join(os.environ.get("LOCALAPPDATA", ""), "Roblox",    "logs"),
    os.path.join(os.environ.get("LOCALAPPDATA", ""), "Bloxstrap",  "Logs"),
    os.path.join(os.environ.get("LOCALAPPDATA", ""), "Fishstrap",  "Logs"),
]
ROBLOX_LOGS_DIR = _ROBLOX_LOG_DIRS[0]

_LOG_PID_RE = re.compile(r"(?:^|[_\-])(\d{4,8})(?:[_\-]|$)")


def _get_running_roblox_pids():
    """Return set of PIDs for all running Roblox player processes."""
    pids = set()
    exe_names = [
        "RobloxPlayerBeta.exe", "RobloxPlayer.exe",
        "Windows10Universal.exe", "RobloxApp.exe",
    ]
    for exe in exe_names:
        try:
            out = subprocess.check_output(
                ["tasklist", "/FI", f"IMAGENAME eq {exe}", "/FO", "CSV", "/NH"],
                stderr=subprocess.DEVNULL, timeout=6,
                creationflags=subprocess.CREATE_NO_WINDOW,
            ).decode(errors="ignore")
            for line in out.splitlines():
                parts = [p.strip('"') for p in line.strip().split('","')]
                if len(parts) >= 2 and parts[1].isdigit():
                    pids.add(int(parts[1]))
        except Exception:
            pass
    return pids


def _all_log_files(max_age_h=6):
    """
    Return log files that belong to CURRENTLY RUNNING Roblox processes.
    Falls back to mtime filter (2 min) only when PID check unavailable.
    """
    all_found = []
    cutoff = time.time() - max_age_h * 3600
    for d in _ROBLOX_LOG_DIRS:
        if not os.path.isdir(d):
            continue
        for fname in os.listdir(d):
            if not fname.endswith(".log"):
                continue
            if any(skip in fname for skip in ("Installer", "bootstrapper", "Studio")):
                continue
            full = os.path.join(d, fname)
            try:
                if os.path.getmtime(full) >= cutoff:
                    all_found.append(full)
            except OSError:
                pass

    if not all_found:
        return []

    running_pids = _get_running_roblox_pids()

    if not running_pids:
        return []

    validated = []
    unmatched = []
    for f in all_found:
        pid = _pid_from_log_filename(f)
        if pid and pid in running_pids:
            validated.append(f)
        else:
            unmatched.append(f)

    if validated:
        validated.sort(key=os.path.getmtime, reverse=True)
        return validated

    fresh_cutoff = time.time() - 120
    fresh = [f for f in unmatched if os.path.getmtime(f) >= fresh_cutoff]
    fresh.sort(key=os.path.getmtime, reverse=True)
    return fresh[:len(running_pids)]


def _pid_from_log_filename(fname):
    """Extract the Roblox process PID embedded in a log filename, or None."""
    base = os.path.basename(fname)
    candidates = []
    for m in _LOG_PID_RE.finditer(base):
        try:
            pid = int(m.group(1))
            if 1000 <= pid <= 9_999_999:
                candidates.append(pid)
        except ValueError:
            pass
    if not candidates:
        return None
    candidates.sort(key=lambda p: abs(len(str(p)) - 5))
    return candidates[0]


class DetectionManager:
    """
    PID-aware log watcher.

    Flow:
      1. Every poll, resolve each account's log file:
           a. PID registered via register_pid()  →  direct PID→log match
           b. Username scan of log content       →  fallback
           c. Single-account + newest log        →  last-resort fallback
      2. For each log, tail new bytes since session_start watermark.
      3. Extract biome (largeImage hoverText) and aura (state field).
      4. On change, fire webhook for that account's discord_webhook field
         AND any global webhooks targeting that account.
    """

    def __init__(self, app):
        self.app                       = app
        self.biome_data                = BIOME_DATA
        self.log_arrays                = []
        self.pid_log_map               = {}
        self.username_log_map          = {}
        self.username_pid_map          = {}
        self.last_log_array_update     = 0
        self.account_biomes            = {}
        self.account_auras             = {}
        self.account_aura_offsets      = {}
        self._aura_fire_lock           = threading.Lock()
        self.log_start_offsets         = {}
        self.app_start_time            = time.time()
        self.last_webhook_time         = 0
        self.webhook_rate_limit        = DEFAULT_WEBHOOK_RATE_LIMIT
        self.account_last_sent_webhook = {}
        self.sent_webhooks_cache       = set()
        threading.Thread(target=self._update_log_map, daemon=True).start()


    def register_pid(self, username, pid):
        pid = int(pid)
        self.username_pid_map[username.lower()] = pid
        self._map_pid_to_log(pid)
        if pid in self.pid_log_map:
            self.username_log_map[username.lower()] = self.pid_log_map[pid]
        print(f"[DetectionManager] registered PID {pid} → '{username}'")

    def _map_pid_to_log(self, pid):
        """Scan all log dirs for a file whose name embeds pid."""
        for log_path in _all_log_files(max_age_h=6):
            if _pid_from_log_filename(log_path) == pid:
                self.pid_log_map[pid] = log_path
                return log_path
        return None


    def _update_log_map(self):
        """
        Rebuild the log map by scanning live log files for configured usernames.
        Only assigns logs to accounts that are actually configured in self.app.accounts.
        """
        try:
            files = _all_log_files(max_age_h=6)
            self.log_arrays = files
            self.pid_log_map = {}
            self.username_log_map = {}

            if not files:
                self.last_log_array_update = time.time()
                return

            for f in files:
                pid = _pid_from_log_filename(f)
                if pid and pid not in self.pid_log_map:
                    self.pid_log_map[pid] = f

            configured = [
                a.get("roblox_username", "").strip()
                for a in getattr(self.app, "accounts", [])
                if a.get("roblox_username", "").strip()
            ]
            if not configured:
                self.last_log_array_update = time.time()
                return

            for log_path in files:
                try:
                    size = os.path.getsize(log_path)
                    with open(log_path, "rb") as f:
                        head = f.read(min(3 * 1024 * 1024, size))
                        tail = b""
                        if size > 3 * 1024 * 1024:
                            f.seek(size - 512 * 1024)
                            tail = f.read()
                    text = (head + tail).decode("utf-8", errors="ignore")
                except Exception:
                    continue

                for uname in configured:
                    key = uname.lower()
                    if key in self.username_log_map:
                        continue
                    patterns = [
                        f"Players.{uname}.",
                        f"players.{uname.lower()}.",
                        f'"{uname}"',
                        uname,
                    ]
                    for pat in patterns:
                        if pat.lower() in text.lower():
                            self.username_log_map[key] = log_path
                            print(f"[DetectionManager] matched '{uname}' → {os.path.basename(log_path)}")
                            break

            self.last_log_array_update = time.time()
            print(f"[DetectionManager] log map: {len(files)} live files, "
                  f"matched {len(self.username_log_map)}/{len(configured)} accounts")
        except Exception as ex:
            import traceback
            print(f"[DetectionManager] _update_log_map error: {ex}")
            traceback.print_exc()

    def _log_contains_username(self, log_path, username):
        """Return True if username appears in the log file."""
        try:
            size = os.path.getsize(log_path)
            with open(log_path, "rb") as f:
                text = f.read(min(3 * 1024 * 1024, size)).decode("utf-8", errors="ignore")
            return username.lower() in text.lower()
        except Exception:
            return False

    def _get_log_for_user(self, username):
        """Return the log path for a configured account username, or None."""
        if time.time() - self.last_log_array_update > LOG_UPDATE_INTERVAL:
            self._update_log_map()

        key = username.lower()

        log = self.username_log_map.get(key)
        if log and os.path.isfile(log):
            return log

        pid = self.username_pid_map.get(key)
        if pid:
            log = self.pid_log_map.get(pid)
            if log and os.path.isfile(log):
                return log

        configured = [
            a.get("roblox_username", "").strip()
            for a in getattr(self.app, "accounts", [])
            if a.get("roblox_username", "").strip()
        ]
        if len(configured) == 1 and configured[0].lower() == key and len(self.log_arrays) == 1:
            return self.log_arrays[0]

        return None

    _LARGE_HOVER_RE = re.compile(
        r'"largeImage"\s*:\s*\{[^}]*"hoverText"\s*:\s*"([^"]+)"',
        re.IGNORECASE | re.DOTALL
    )
    _ANY_HOVER_RE = re.compile(r'"hoverText"\s*:\s*"([^"]+)"', re.IGNORECASE)
    _PLAIN_BIOME_RE = re.compile(
        r'(?:Changing biome to|Current biome[: ]+|Biome[: ]+|biome changed to|biome:)\s*'
        r'([A-Z][A-Z0-9 _]{1,30})',
        re.IGNORECASE
    )
    _STATE_RE = re.compile(r'"state"\s*:\s*"([^"]{1,200})"', re.IGNORECASE)
    _no_biome_warned: set = set()

    def _get_biome_from_log_tail(self, log_path, start_offset=0):
        try:
            size = os.path.getsize(log_path)
            if size <= start_offset:
                return None
            with open(log_path, "rb") as f:
                read_from = max(start_offset, size - LOG_TAIL_READ_BYTES)
                f.seek(read_from)
                tail = f.read().decode("utf-8", errors="ignore")
        except Exception:
            return None
        return self._extract_biome(tail, log_path=log_path)

    def _extract_biome(self, text, log_path=None):
        known_upper = {n.upper() for n in self.biome_data}
        known_upper.update({"SAND STORM", "SANDSTORM", "NORMAL"})

        def _match(raw):
            v = raw.strip().upper()
            if v == "SANDSTORM":
                v = "SAND STORM"
            if v in known_upper and v not in ("NORMAL", "SOL'S RNG", "SOL'S RNG"):
                return v
            for k in sorted(known_upper, key=len, reverse=True):
                if k in ("NORMAL",):
                    continue
                if k in v:
                    return "SAND STORM" if k == "SANDSTORM" else k
            return None

        last = None
        for m in self._LARGE_HOVER_RE.finditer(text):
            hit = _match(m.group(1))
            if hit:
                last = hit
        if last:
            return last

        for m in self._ANY_HOVER_RE.finditer(text):
            hit = _match(m.group(1))
            if hit:
                last = hit
        if last:
            return last

        for m in self._PLAIN_BIOME_RE.finditer(text):
            v = m.group(1).strip().upper()
            if v == "SANDSTORM":
                v = "SAND STORM"
            if v in known_upper:
                last = v
        if last:
            return last

        key = log_path or "__unknown__"
        if key not in DetectionManager._no_biome_warned:
            DetectionManager._no_biome_warned.add(key)
            snippet = text[-300:].replace("\n", " ").strip()
            print(f"[DetectionManager] no biome in tail (won't repeat). last 300: {snippet!r}")
        return None

    def _extract_biome_from_rpc(self, text, log_path=None):
        return self._extract_biome(text, log_path=log_path)


    _AURA_RE_ESC      = re.compile(r'"state"\s*:\s*"Equipped\s+\\"([^\\"]+)\\"', re.IGNORECASE)
    _AURA_RE_STRAIGHT = re.compile(r'"state"\s*:\s*"Equipped\s+"([^"]+)"',        re.IGNORECASE)
    _AURA_RE_BARE     = re.compile(r'"state"\s*:\s*"Equipped\s+([^"\\,}]+?)\s*"', re.IGNORECASE)
    _AURA_RE_PLAIN    = re.compile(
        r'(?:You equipped|Equipped aura|Aura equipped)[:\s]+([^\r\n\[]+)', re.IGNORECASE)

    @staticmethod
    def _match_aura_name(raw):
        stripped = raw.strip().rstrip('."!')
        key = stripped.lower()
        if key in AURA_LOOKUP:
            return AURA_LOOKUP[key][0]
        norm = re.sub(r'\s*[:/-]\s*', ': ', key)
        if norm in AURA_LOOKUP:
            return AURA_LOOKUP[norm][0]
        for lk, (canonical, _) in AURA_LOOKUP.items():
            if lk == key or lk == norm:
                return canonical
        return None

    def _extract_aura(self, text, base_offset=0):
        """Return (canonical_name, abs_offset) of the last aura equip, or (None, -1)."""
        last, last_pos = None, -1
        for pat in (self._AURA_RE_ESC, self._AURA_RE_STRAIGHT,
                    self._AURA_RE_BARE, self._AURA_RE_PLAIN):
            for m in pat.finditer(text):
                canonical = self._match_aura_name(m.group(1))
                if canonical and m.start() > last_pos:
                    last, last_pos = canonical, m.start()
        return last, (base_offset + last_pos if last_pos >= 0 else -1)

    def _get_aura_from_log_tail(self, log_path, start_offset=0):
        try:
            size = os.path.getsize(log_path)
            if size <= start_offset:
                return None, -1
            with open(log_path, "rb") as f:
                read_from = max(start_offset, size - LOG_TAIL_READ_BYTES)
                f.seek(read_from)
                raw = f.read()
        except Exception:
            return None, -1

        base     = read_from
        raw_text = raw.decode("utf-8", errors="ignore")

        name, pos = self._extract_aura(raw_text, base_offset=base)
        if name:
            return name, pos

        unesc = raw_text.replace('\\"', '"').replace('\\\\', '\\')
        name, pos = self._extract_aura(unesc, base_offset=base)
        return name, pos


    def _get_account_webhook(self, username):
        """Return the discord_webhook configured for this account, or ''."""
        for acct in self.app.accounts:
            if acct.get("roblox_username", "").lower() == username.lower():
                return acct.get("discord_webhook", "").strip()
        return ""

    def _fire_biome_webhook(self, username, biome, private_server,
                            ping_everyone=False, force_notify=False):
        """Send biome alert to all applicable webhooks for this account."""
        self.app.root.after(
            0,
            lambda u=username, b=biome, p=private_server, pe=ping_everyone, fn=force_notify:
                self.app._on_account_biome_change(u, b, p, ping_everyone=pe, force_notify=fn)
        )

    def _fire_aura_webhook(self, username, aura, odds, private_server):
        """Send aura alert to all applicable webhooks for this account."""
        self.app.root.after(
            0,
            lambda u=username, a=aura, o=odds, p=private_server:
                self.app._on_account_aura_detected(u, a, o, p)
        )


    def check_single_account(self, username):
        log_path = self._get_log_for_user(username)
        if not log_path:
            return

        first_check = log_path not in self.log_start_offsets

        if first_check:
            try:
                file_end = os.path.getsize(log_path)
            except Exception:
                file_end = 0
            self.log_start_offsets[log_path] = file_end

            seed = self._get_biome_from_log_tail(log_path, 0)
            if seed:
                matched = next(
                    (n for n in self.biome_data if n.upper() == seed.upper()),
                    next((n for n, *_ in BIOMES if n.upper() == seed.upper()), None)
                )
                if matched:
                    self.account_biomes[username] = matched

            self.account_aura_offsets[username] = file_end
            return

        session_start = self.log_start_offsets[log_path]

        current_aura, aura_offset = self._get_aura_from_log_tail(log_path, session_start)
        last_offset = self.account_aura_offsets.get(username, -1)

        if current_aura and aura_offset > last_offset:
            with self._aura_fire_lock:
                if aura_offset > self.account_aura_offsets.get(username, -1):
                    self.account_aura_offsets[username] = aura_offset
                    if current_aura != self.account_auras.get(username):
                        self.account_auras[username] = current_aura
                        aura_info   = AURA_LOOKUP.get(current_aura.lower(), (current_aura, "?"))
                        ps_for_aura = self._get_account_ps(username)
                        print(f"[DetectionManager] aura equipped '{username}': {current_aura}")
                        self._fire_aura_webhook(username, current_aura, aura_info[1], ps_for_aura)

        current_biome = self._get_biome_from_log_tail(log_path, session_start)
        if not current_biome:
            display_biome = self._get_biome_from_log_tail(log_path, 0)
            if display_biome:
                matched_d = next(
                    (n for n in self.biome_data if n.upper() == display_biome.upper()),
                    next((n for n, *_ in BIOMES if n.upper() == display_biome.upper()), None)
                )
                if matched_d and matched_d != self.account_biomes.get(username):
                    self.account_biomes[username] = matched_d
            return

        matched = None
        for known in list(self.biome_data) + [n for n, *_ in BIOMES]:
            if known.upper() == current_biome.upper():
                matched = known
                break
        if not matched:
            return

        if matched == self.account_biomes.get(username):
            return

        self.account_biomes[username] = matched
        biome_info = self.biome_data.get(matched, {})
        if biome_info.get("never_notify"):
            return

        if hasattr(self.app, "biome_counts"):
            self.app.biome_counts[matched] = self.app.biome_counts.get(matched, 0) + 1
            try:
                lw = self.app._biome_count_labels.get(matched)
                if lw:
                    lw.config(text=str(self.app.biome_counts[matched]), fg=ACCENT)
            except Exception:
                pass

        print(f"[DetectionManager] biome change for '{username}': {matched}")
        self._fire_biome_webhook(
            username, matched,
            self._get_account_ps(username),
            ping_everyone=biome_info.get("ping_everyone", False),
            force_notify=biome_info.get("force_notify", False),
        )

    def _get_account_ps(self, username):
        for acct in self.app.accounts:
            if acct.get("roblox_username", "").lower() == username.lower():
                return acct.get("private_server", "")
        return ""

    def reset(self):
        self.account_biomes       = {}
        self.account_auras        = {}
        self.account_aura_offsets = {}
        self.log_start_offsets    = {}
        self.sent_webhooks_cache  = set()
        self.username_pid_map     = {}
        DetectionManager._no_biome_warned.clear()
        self._update_log_map()
    """
    PID-aware detection manager.

    When accounts are launched, their Roblox PID is registered via
    register_pid(username, pid).  The manager maps each PID to its log file
    (log filenames embed the PID), so two accounts in separate Roblox windows
    are tracked independently even if they logged in at the same time.

    Fallback: if no PID is registered, the old Players.X.PlayerGui scan is used.
    """

    def __init__(self, app):
        self.app                       = app
        self.biome_data                = BIOME_DATA
        self.log_arrays                = []
        self.username_log_map          = {}
        self.pid_log_map               = {}
        self.username_pid_map          = {}
        self.last_log_array_update     = 0
        self.account_biomes            = {}
        self.account_auras             = {}
        self.account_aura_offsets      = {}
        self._aura_fire_lock           = threading.Lock()
        self.log_start_offsets         = {}
        self.app_start_time            = time.time()
        self.last_webhook_time         = 0
        self.webhook_rate_limit        = DEFAULT_WEBHOOK_RATE_LIMIT
        self.account_last_sent_webhook = {}
        self.sent_webhooks_cache       = set()
        threading.Thread(target=self._update_log_map, daemon=True).start()


    def register_pid(self, username, pid):
        """
        Associate a Roblox PID with an account username.
        The manager will find the matching log file and use it for detection.
        """
        pid = int(pid)
        self.username_pid_map[username.lower()] = pid
        self._map_pid_to_log(pid)
        print(f"[DetectionManager] registered PID {pid} for '{username}'")

    def _map_pid_to_log(self, pid):
        """Find the log file whose filename contains 'pid' and cache it."""
        if not os.path.isdir(ROBLOX_LOGS_DIR):
            return
        pid_str = str(pid)
        for fname in os.listdir(ROBLOX_LOGS_DIR):
            if not fname.endswith(".log"):
                continue
            m = _LOG_PID_RE.search(fname)
            if m and m.group(1) == pid_str:
                full = os.path.join(ROBLOX_LOGS_DIR, fname)
                self.pid_log_map[pid] = full
                return


    def check_all_accounts(self):
        """Multithreaded biome check for all configured accounts."""
        if not self.app.accounts:
            return

        if time.time() - self.last_log_array_update > LOG_UPDATE_INTERVAL:
            self._update_log_map()

        usernames = [a.get("roblox_username", "") for a in self.app.accounts
                     if a.get("roblox_username")]
        if not usernames:
            return

        if len(self.sent_webhooks_cache) > 200:
            self.sent_webhooks_cache = set(list(self.sent_webhooks_cache)[-100:])

        max_workers = max(1, len(usernames))
        with __import__("concurrent.futures", fromlist=["ThreadPoolExecutor"]).ThreadPoolExecutor(
                max_workers=max_workers) as ex:
            futures = {ex.submit(self.check_single_account, u): u for u in usernames}
            for f in futures:
                try:
                    f.result()
                except Exception as e:
                    print(f"[DetectionManager] error for {futures[f]}: {e}")

    def reset(self):
        """Call when the accounts list changes."""
        self.account_biomes      = {}
        self.log_start_offsets   = {}
        self.username_log_map    = {}
        DetectionManager._no_biome_warned.clear()
        self.sent_webhooks_cache = set()
        self.username_pid_map    = {}
        DetectionManager._no_biome_warned.clear()
        self._update_log_map()


_AGREEMENT_FILE = os.path.join(
    os.path.dirname(sys.executable) if getattr(sys, "frozen", False)
    else os.path.dirname(os.path.abspath(__file__)),
    ".agreed"
)

def _has_agreed():
    """Return True if the user has previously agreed to the license."""
    try:
        return os.path.exists(_AGREEMENT_FILE) and open(_AGREEMENT_FILE).read().strip() == "1"
    except Exception:
        return False

def _save_agreement():
    try:
        with open(_AGREEMENT_FILE, "w") as f:
            f.write("1")
    except Exception:
        pass

def _show_agreement_dialog():
    """
    Show a full-screen-style user agreement window.
    Returns True if the user agreed, False if they declined (app should exit).
    Already agreed → returns True immediately without showing the dialog.
    """
    if _has_agreed():
        return True

    agreed = [False]

    root = tk.Tk()
    root.title("MultiFInstance — License Agreement")
    root.configure(bg="#0b0d13")
    root.resizable(False, False)

    W, H = 680, 560
    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    root.geometry(f"{W}x{H}+{(sw-W)//2}+{(sh-H)//2}")

    try:
        root.overrideredirect(False)
    except Exception:
        pass

    BG   = "#0b0d13"
    CARD = "#111520"
    BDR  = "#1c2035"
    ACC  = "#5865f2"
    RED  = "#e05068"
    TP   = "#dde2f4"
    TM   = "#c0c6dc"
    TF   = "#7e8aaa"

    hdr = tk.Frame(root, bg=CARD, highlightthickness=1, highlightbackground=BDR)
    hdr.pack(fill="x")

    tk.Label(hdr, text="◈  MultiFInstance", fg=ACC, bg=CARD,
             font=("Segoe UI", 13, "bold"), pady=14, padx=18).pack(side="left")
    tk.Label(hdr, text="License Agreement", fg=TF, bg=CARD,
             font=("Segoe UI", 9)).pack(side="left")

    mid = tk.Frame(root, bg=BG)
    mid.pack(fill="both", expand=True, padx=18, pady=(14, 0))

    tk.Label(mid, text="Please read the full license before using MultiFInstance.",
             fg=TM, bg=BG, font=("Segoe UI", 9)).pack(anchor="w", pady=(0, 6))

    txt_frame = tk.Frame(mid, bg=CARD, highlightthickness=1, highlightbackground=BDR)
    txt_frame.pack(fill="both", expand=True)

    sb  = tk.Scrollbar(txt_frame, bg=CARD, troughcolor=BG, relief="flat", bd=0)
    sb.pack(side="right", fill="y")

    txt = tk.Text(
        txt_frame, bg="#0d1019", fg=TM, font=("Consolas", 8),
        relief="flat", bd=0, wrap="word",
        highlightthickness=0,
        yscrollcommand=sb.set,
        state="normal", cursor="arrow",
        insertwidth=0, padx=12, pady=10,
    )
    txt.pack(side="left", fill="both", expand=True)
    sb.config(command=txt.yview)

    txt.insert("1.0", _LICENSE_TEXT)
    txt.config(state="disabled")

    txt.bind("<MouseWheel>", lambda e: txt.yview_scroll(int(-1*(e.delta/120)), "units"))
    txt.bind("<Button-4>",   lambda e: txt.yview_scroll(-1, "units"))
    txt.bind("<Button-5>",   lambda e: txt.yview_scroll(1, "units"))

    bot = tk.Frame(root, bg=BG)
    bot.pack(fill="x", padx=18, pady=14)

    check_var = tk.BooleanVar(value=False)
    check_row = tk.Frame(bot, bg=BG)
    check_row.pack(anchor="w", pady=(0, 10))

    cb = tk.Checkbutton(check_row, variable=check_var, bg=BG,
                        activebackground=BG, fg=TP,
                        selectcolor="#1c1e2e", relief="flat", bd=0,
                        cursor="hand2", font=("Segoe UI", 9),
                        text="  I have read and agree to the license terms above")
    cb.pack(side="left")

    btn_row = tk.Frame(bot, bg=BG)
    btn_row.pack(anchor="e")

    def _decline():
        agreed[0] = False
        root.destroy()

    def _agree():
        if not check_var.get():
            cb.config(fg="#e05068")
            root.after(800, lambda: cb.config(fg=TP))
            return
        _save_agreement()
        agreed[0] = True
        root.destroy()

    no_btn = tk.Button(
        btn_row, text="No, close",
        fg=RED, bg="#1c0c10", font=("Segoe UI", 9, "bold"),
        relief="flat", bd=0, cursor="hand2",
        activeforeground=RED, activebackground="#240f15",
        command=_decline, padx=20, pady=8,
        highlightthickness=1, highlightbackground="#3a1520",
    )
    no_btn.pack(side="left", padx=(0, 10))
    no_btn.bind("<Enter>", lambda e: no_btn.config(bg="#240f15"))
    no_btn.bind("<Leave>", lambda e: no_btn.config(bg="#1c0c10"))

    yes_btn = tk.Button(
        btn_row, text="Yes, I agree  →",
        fg="#061510", bg=ACC, font=("Segoe UI", 9, "bold"),
        relief="flat", bd=0, cursor="hand2",
        activeforeground="#061510", activebackground="#4752c4",
        command=_agree, padx=20, pady=8,
    )
    yes_btn.pack(side="left")
    yes_btn.bind("<Enter>", lambda e: yes_btn.config(bg="#4752c4"))
    yes_btn.bind("<Leave>", lambda e: yes_btn.config(bg=ACC))

    root.bind("<Return>", lambda e: _agree())
    root.bind("<Escape>", lambda e: _decline())

    root.protocol("WM_DELETE_WINDOW", _decline)
    root.focus_force()
    root.mainloop()
    return agreed[0]

class MultiFInstanceApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"MultiFInstance v{VERSION}")
        global _ANIM_ROOT
        _ANIM_ROOT = self.root
        self.root.configure(bg=BG_BASE)
        self.root.resizable(True, True)

        self.running         = False
        self.macro_start     = None
        self.biome_counts    = {n: 0 for n in BIOME_DATA}
        self.active_page     = None
        self._tip_win        = None
        self._dash_alive     = False
        self._page_cache     = {}
        self._transitioning  = False
        self._toast_win      = None
        self._roblox_mutexes = []

        self._avatar_cache          = {}
        self._avatar_canvas_registry = {}
        self._last_active_usernames = []
        self._biome_label_map       = {}

        self._detection_mgr  = None

        self._antiafk_running       = False
        self._antiafk_stop_event    = threading.Event()
        self._antiafk_thread        = None
        self._antiafk_interval      = tk.IntVar(value=120)
        self._antiafk_action        = tk.StringVar(value="click")
        self._antiafk_user_safe     = tk.BooleanVar(value=False)
        self._antiafk_sequential    = tk.BooleanVar(value=False)
        self._antiafk_seq_delay     = tk.DoubleVar(value=0.75)
        self._antiafk_last_activity = time.time()
        self._antiafk_monitor_stop  = threading.Event()
        self._antiafk_user_active   = False
        self._antiafk_monitor_thread = None
        self._afk_click_x_pct   = tk.IntVar(value=50)
        self._afk_click_y_pct   = tk.IntVar(value=50)
        self._afk_click_hold_ms = tk.IntVar(value=80)

        self._activity_log   = []
        self._activity_lbl_list = []

        self.instances = []
        self._next_inst_id = 1

        self.accounts = []

        self.webhooks = []

        self.biome_alert_vars  = {}
        self.discord_user_id   = tk.StringVar()
        self._pending_biome_alerts = {}

        w, h = 840, 580
        self.root.geometry(f"{w}x{h}")
        self.root.minsize(720, 500)
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

        self.root.attributes("-alpha", 0.0)

        self.root.overrideredirect(True)
        try:
            self.root.withdraw()
            self.root.update_idletasks()

            GWL_EXSTYLE       = -20
            GWL_STYLE         = -16
            WS_CAPTION        = 0x00C00000
            WS_THICKFRAME     = 0x00040000
            WS_MINIMIZEBOX    = 0x00020000
            WS_MAXIMIZEBOX    = 0x00010000
            WS_SYSMENU        = 0x00080000
            WS_EX_APPWINDOW   = 0x00040000
            WS_EX_TOOLWINDOW  = 0x00000080
            SWP_FLAGS         = 0x0001 | 0x0002 | 0x0004 | 0x0020

            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())

            style   = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_STYLE)
            exstyle = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)

            style   = (style | WS_THICKFRAME | WS_MINIMIZEBOX | WS_MAXIMIZEBOX | WS_SYSMENU) & ~WS_CAPTION
            exstyle = (exstyle | WS_EX_APPWINDOW) & ~WS_EX_TOOLWINDOW

            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_STYLE,   style)
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, exstyle)

            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE,
                ctypes.byref(ctypes.c_int(1)), ctypes.sizeof(ctypes.c_int))

            ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, SWP_FLAGS)

            self._hwnd = hwnd

            self.root.deiconify()
            self.root.update_idletasks()
        except Exception:
            self._hwnd = None
            try:
                self.root.deiconify()
            except Exception:
                pass

        self._is_maximized  = False
        self._restore_geo   = None
        self._drag_start_x  = 0
        self._drag_start_y  = 0

        self._load_config()
        self._build_ui()
        self._navigate("dashboard")
        self._prebuild_pages()

        self.root.bind("<F8>", lambda e: self._toggle_macro())
        self.root.bind("<F9>", lambda e: self._toggle_antiafk())

        self._tick_auto_scan()
        self._tick_log_watcher()

        self._tick_autosave()

        threading.Thread(target=self._setup_roblox_feature_flags, daemon=True).start()

        self._detection_mgr = DetectionManager(self)

        threading.Thread(target=self._kill_singleton_mutex, daemon=True).start()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self.root.after(80, lambda: self._startup_fade(alpha=0.0))

    def _build_ui(self):
        self.root.rowconfigure(1, weight=1)
        self.root.columnconfigure(1, weight=1)
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TCombobox",
                        fieldbackground=BG_ITEM,
                        background=BG_ITEM,
                        foreground=TEXT_MUTED,
                        bordercolor=BORDER_ITEM,
                        arrowcolor=TEXT_DIM,
                        selectbackground=ACCENT_DIM,
                        selectforeground=TEXT_PRIMARY)
        style.map("TCombobox",
                  fieldbackground=[("readonly", BG_ITEM)],
                  foreground=[("readonly", TEXT_MUTED)],
                  background=[("readonly", BG_ITEM)])
        self._build_topbar()
        self._build_sidebar()
        self._content = fr(self.root, bg=BG_BASE)
        self._content.grid(row=1, column=1, sticky="nsew")
        self._content.rowconfigure(0, weight=1)
        self._content.columnconfigure(0, weight=1)

    def _build_topbar(self):
        TB_H  = 48
        TB_BG = BG_SIDEBAR

        bar = tk.Frame(self.root, bg=TB_BG, height=TB_H, bd=0)
        bar.grid(row=0, column=0, columnspan=2, sticky="ew")
        bar.grid_propagate(False)
        self._topbar = bar

        def _drag_start(e):
            if self._is_maximized:
                return
            self._drag_start_x = e.x_root
            self._drag_start_y = e.y_root
            self._drag_win_x   = self.root.winfo_x()
            self._drag_win_y   = self.root.winfo_y()

        def _drag_motion(e):
            if self._is_maximized:
                return
            new_x = self._drag_win_x + (e.x_root - self._drag_start_x)
            new_y = self._drag_win_y + (e.y_root - self._drag_start_y)
            try:
                SWP_NOSIZE      = 0x0001
                SWP_NOZORDER    = 0x0004
                SWP_NOACTIVATE  = 0x0010
                hwnd = self._hwnd or ctypes.windll.user32.GetParent(self.root.winfo_id())
                ctypes.windll.user32.SetWindowPos(
                    hwnd, 0, new_x, new_y, 0, 0,
                    SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE)
            except Exception:
                self.root.geometry(f"+{new_x}+{new_y}")

        def _drag_dbl(e):
            self._toggle_maximize()

        for w in [bar]:
            w.bind("<ButtonPress-1>",   _drag_start)
            w.bind("<B1-Motion>",       _drag_motion)
            w.bind("<Double-Button-1>", _drag_dbl)

        title_f = fr(bar, bg=TB_BG, cursor="fleur")
        title_f.pack(side="left", padx=(16, 0), fill="y")
        title_f.bind("<ButtonPress-1>",   _drag_start)
        title_f.bind("<B1-Motion>",       _drag_motion)
        title_f.bind("<Double-Button-1>", _drag_dbl)

        lbl(title_f, "MultiFInstance", fg=TEXT_PRIMARY, bg=TB_BG,
            font=("Segoe UI", 13, "bold"), cursor="fleur").pack(side="left")
        lbl(title_f, f"  v{VERSION}", fg=TEXT_FAINT, bg=TB_BG,
            font=("Segoe UI", 9), cursor="fleur").pack(side="left")

        right = fr(bar, bg=TB_BG)
        right.pack(side="right", fill="y")

        ctrl_f = fr(right, bg=TB_BG)
        ctrl_f.pack(side="right", padx=(0, 8), pady=0, fill="y")

        def _wc_btn(parent, symbol, normal_bg, hover_bg, hover_fg, cmd):
            BTN_SZ = 28
            c = tk.Canvas(parent, width=BTN_SZ, height=BTN_SZ,
                          bg=normal_bg, highlightthickness=0, bd=0, cursor="hand2")
            c.create_text(BTN_SZ//2, BTN_SZ//2 + 1, text=symbol,
                          fill=TEXT_FAINT, font=("Segoe UI", 10), tags="sym")
            def _enter(e):
                c.config(bg=hover_bg)
                c.itemconfig("sym", fill=hover_fg)
            def _leave(e):
                c.config(bg=normal_bg)
                c.itemconfig("sym", fill=TEXT_FAINT)
            c.bind("<Enter>", _enter)
            c.bind("<Leave>", _leave)
            c.bind("<ButtonRelease-1>", lambda e: cmd())
            c.pack(side="right", padx=1, pady=10)
            return c

        _wc_btn(ctrl_f, "✕", TB_BG, "#c0392b", "#ffffff", self._on_close)
        self._wc_max = _wc_btn(ctrl_f, "□", TB_BG, ACCENT_DIM, ACCENT,
                                self._toggle_maximize)
        _wc_btn(ctrl_f, "–", TB_BG, BG_ITEM, TEXT_PRIMARY, self._minimize_window)

        cred_row = fr(right, bg=TB_BG, cursor="hand2")
        cred_row.pack(side="right", padx=(0, 8), fill="y")
        cred_row.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/pws32z"))

        cred_av = tk.Canvas(cred_row, width=20, height=20, bg=TB_BG,
                            highlightthickness=0, bd=0, cursor="hand2")
        cred_av.create_oval(1, 1, 19, 19, fill=ACCENT_DIM, outline="", tags="bg")
        cred_av.create_text(10, 10, text="P", fill=TEXT_PRIMARY,
                            font=("Segoe UI", 7, "bold"), tags="ph")
        cred_av.pack(side="left", padx=(0, 4))
        cred_av.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/pws32z"))

        cred = lbl(cred_row, "pws32z", fg=TEXT_FAINT, bg=TB_BG,
                   font=("Segoe UI", 9), cursor="hand2")
        cred.pack(side="left")
        cred.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/pws32z"))

        def _load_cred_avatar():
            photo = _load_embedded_image(_PWS32Z_AVATAR_B64, 20)
            if photo:
                self._cred_avatar_photo = photo
                def _draw():
                    try:
                        cred_av.delete("all")
                        cred_av.create_image(0, 0, anchor="nw", image=photo)
                    except Exception:
                        pass
                self.root.after(0, _draw)
        threading.Thread(target=_load_cred_avatar, daemon=True).start()

        def _cred_enter(e): _anim_fg(cred, TEXT_FAINT, ACCENT)
        def _cred_leave(e): _anim_fg(cred, ACCENT, TEXT_FAINT)
        for w in [cred_row, cred_av, cred]:
            w.bind("<Enter>", _cred_enter)
            w.bind("<Leave>", _cred_leave)

        pill = fr(right, bg=RED_BG)
        pill.config(highlightthickness=1, highlightbackground="#3a1520")
        pill.pack(side="right", padx=(0, 10), pady=12, fill="y")
        self._topbar_status_dot = tk.Canvas(pill, width=8, height=8,
                                            bg=RED_BG, highlightthickness=0)
        self._topbar_status_dot.create_oval(1, 1, 7, 7, fill=RED, outline="", tags="d")
        self._topbar_status_dot.pack(side="left", padx=(9, 3), pady=5)
        self._topbar_status_lbl = lbl(pill, "Stopped",
                                      fg=RED, bg=RED_BG,
                                      font=("Segoe UI", 9, "bold"))
        self._topbar_status_lbl.pack(side="left", padx=(0, 9))
        self._topbar_status_pill = pill

    def _minimize_window(self):
        """Minimize the window — appears in taskbar, click to restore."""
        try:
            if self._hwnd:
                ctypes.windll.user32.ShowWindow(self._hwnd, 6)
                return
        except Exception:
            pass
        self.root.iconify()

    def _toggle_maximize(self):
        if self._is_maximized:
            if self._restore_geo:
                self.root.geometry(self._restore_geo)
            self._is_maximized = False
            try:
                self._wc_max.itemconfig("sym", text="□")
            except Exception:
                pass
        else:
            self._restore_geo = self.root.geometry()
            try:
                import ctypes
                class RECT(ctypes.Structure):
                    _fields_ = [("left",ctypes.c_long),("top",ctypes.c_long),
                                ("right",ctypes.c_long),("bottom",ctypes.c_long)]
                r = RECT()
                ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(r), 0)
                w = r.right - r.left
                h = r.bottom - r.top
                self.root.geometry(f"{w}x{h}+{r.left}+{r.top}")
            except Exception:
                self.root.geometry(
                    f"{self.root.winfo_screenwidth()}x{self.root.winfo_screenheight()}+0+0")
            self._is_maximized = True
            try:
                self._wc_max.itemconfig("sym", text="❐")
            except Exception:
                pass

    def _load_nav_icons(self):
        """
        Load sidebar nav icons from embedded base64 PNGs.
        Falls back gracefully if PIL is unavailable.
        Also tries to load from  assets/imgs/<name>.png  next to the script
        (so if the user puts their own PNGs there they take priority).
        """
        self._nav_icons     = {}
        self._nav_icons_inv = {}
        if not PIL_AVAILABLE:
            return

        import base64 as _b64, io as _io

        SZ         = 20
        TIGHT_KEYS = {"biome_actions"}
        _base      = os.path.dirname(os.path.abspath(__file__))
        _assets    = os.path.join(_base, "assets", "imgs")

        _FNAME = {
            "dashboard":     "dashboard.png",
            "accounts":      "user.png",
            "instances":     "url.png",
            "biome_actions": "activity.png",
            "discord":       "discord.png",
        }

        def _load_img(key):
            local = os.path.join(_assets, _FNAME[key])
            if os.path.exists(local):
                try:
                    return Image.open(local).convert("RGBA")
                except Exception:
                    pass
            b64 = _ICON_B64_MAP.get(key)
            if b64:
                try:
                    data = _b64.b64decode(b64)
                    return Image.open(_io.BytesIO(data)).convert("RGBA")
                except Exception:
                    pass
            return None

        for key in _FNAME:
            try:
                img = _load_img(key)
                if img is None:
                    continue
                if key in TIGHT_KEYS:
                    bbox = img.getbbox()
                    if bbox:
                        img = img.crop(bbox)
                img = img.resize((SZ, SZ), Image.LANCZOS)
                _r, _g, _b, a = img.split()
                norm = Image.new("RGBA", img.size, (107, 114, 144, 0))
                norm.putalpha(a)
                self._nav_icons[key] = ImageTk.PhotoImage(norm)
                acc = Image.new("RGBA", img.size, (88, 101, 242, 0))
                acc.putalpha(a)
                self._nav_icons_inv[key] = ImageTk.PhotoImage(acc)
            except Exception:
                pass

    def _build_sidebar(self):
        self._load_nav_icons()

        SB_W = 68
        self._sb = tk.Frame(self.root, bg=BG_SIDEBAR, width=SB_W, bd=0,
                            highlightthickness=1, highlightbackground=BORDER)
        self._sb.grid(row=1, column=0, sticky="ns")
        self._sb.grid_propagate(False)
        self._nav_btns       = {}
        self._nav_btn_frames = {}

        top = fr(self._sb, bg=BG_SIDEBAR)
        top.pack(side="top", fill="x", pady=(14, 0))

        nav_items = [
            ("dashboard",     "dashboard",     "Dashboard"),
            ("accounts",      "accounts",      "Accounts"),
            ("instances",     "webhooks",      "Webhooks"),
            ("biome_actions", "biome_actions", "Biome Actions"),
            ("antiafk",       "antiafk",       "Anti-AFK"),
        ]
        for icon_key, page_key, tooltip in nav_items:
            self._make_nav_btn(top, icon_key, page_key, tooltip)

        bottom = fr(self._sb, bg=BG_SIDEBAR)
        bottom.pack(side="bottom", fill="x", pady=(0, 12))

        dot_row = fr(bottom, bg=BG_SIDEBAR)
        dot_row.pack(anchor="center")
        self._sb_dot_cv = tk.Canvas(dot_row, width=8, height=8, bg=BG_SIDEBAR,
                                    highlightthickness=0)
        self._sb_dot_cv.create_oval(1, 1, 7, 7, fill=TEXT_FAINTEST, outline="",
                                    tags="dot")
        self._sb_dot_cv.pack()

        tk.Frame(self._sb, bg=BORDER, height=1).pack(
            side="bottom", fill="x", pady=(0, 4))


    def _prebuild_pages(self):
        """Build all page frames up front while the window is hidden.
        This means every tab switch is a simple grid_remove/grid — no build lag."""
        builders = {
            "webhooks":      self._page_webhooks,
            "biome_actions": self._page_biome_actions,
            "launch":        self._page_launch,
            "antiafk":       self._page_antiafk,
            "activity":      self._page_activity,
            "accounts":      self._page_accounts,
        }
        for key, builder in builders.items():
            if key not in self._page_cache:
                try:
                    page = builder(self._content)
                    page.grid(row=0, column=0, sticky="nsew")
                    page.grid_remove()
                    self._page_cache[key] = page
                except Exception:
                    pass

    def _startup_fade(self, alpha=0.0, steps=18, delay=20):
        """Fade the entire window in from transparent on first launch."""
        try:
            self.root.attributes("-alpha", alpha)
        except Exception:
            return
        if alpha >= 1.0:
            return
        next_alpha = min(1.0, alpha + 1.0 / steps)
        self.root.after(delay, lambda: self._startup_fade(next_alpha, steps, delay))

    def _animate_bg(self, widgets, from_col, to_col, steps=8, delay=12):
        """Animate background of a list of widgets using module-level helper."""
        for w in widgets:
            _anim_bg(w, from_col, to_col, steps=steps, delay=delay)

    def _animate_fg(self, widget, from_col, to_col, steps=8, delay=12):
        _anim_fg(widget, from_col, to_col, steps=steps, delay=delay)

    def _animate_bar(self, bar, from_col, to_col, steps=8, delay=12):
        _anim_bg(bar, from_col, to_col, steps=steps, delay=delay)

    def _make_nav_btn(self, parent, icon_key, page_key, tooltip):
        """Polished sidebar nav button with smooth animations."""
        ACTIVE_BG  = "#1c1f2e"
        ACTIVE_BAR = "#5865f2"

        outer = tk.Frame(parent, bg=BG_SIDEBAR, cursor="hand2", bd=0)
        outer.pack(fill="x", pady=2, padx=0)

        bar = tk.Frame(outer, bg=BG_SIDEBAR, width=3)
        bar.pack(side="left", fill="y")

        inner = tk.Frame(outer, bg=BG_SIDEBAR, cursor="hand2")
        inner.pack(side="left", fill="both", expand=True, padx=(4, 6))

        icon_img = self._nav_icons.get(icon_key)
        icon_inv = self._nav_icons_inv.get(icon_key)

        _fallback_text = {
            "dashboard":     "⊞",
            "accounts":      "☻",
            "instances":     "⇄",
            "biome_actions": "◈",
            "antiafk":       "⚙",
        }

        if icon_img:
            ico = tk.Label(inner, image=icon_img, bg=BG_SIDEBAR,
                           cursor="hand2", pady=6)
            ico._img_normal = icon_img
            ico._img_inv    = icon_inv
        else:
            ico = tk.Label(inner, text=_fallback_text.get(icon_key, "●"),
                           bg=BG_SIDEBAR, fg=TEXT_DIM,
                           font=("Segoe UI", 13), cursor="hand2", pady=6)

        ico.pack(fill="x")

        lbl_w = tk.Label(inner, text=tooltip,
                         bg=BG_SIDEBAR, fg=TEXT_FAINT,
                         font=("Segoe UI", 7), cursor="hand2", pady=0)
        lbl_w.pack(fill="x", pady=(0, 5))

        self._nav_btns[page_key]       = ico
        self._nav_btn_frames[page_key] = outer

        all_widgets = [outer, inner, ico, lbl_w]

        def _activate():
            self._animate_bar(bar, BG_SIDEBAR, ACTIVE_BAR, steps=10, delay=10)
            self._animate_bg(all_widgets, BG_SIDEBAR, ACTIVE_BG, steps=10, delay=10)
            self._animate_fg(lbl_w, TEXT_FAINT, ACCENT, steps=10, delay=10)
            if icon_inv:
                ico.config(image=icon_inv)

        def _deactivate():
            self._animate_bar(bar, ACTIVE_BAR, BG_SIDEBAR, steps=10, delay=10)
            self._animate_bg(all_widgets, ACTIVE_BG, BG_SIDEBAR, steps=10, delay=10)
            self._animate_fg(lbl_w, ACCENT, TEXT_FAINT, steps=10, delay=10)
            if icon_img:
                ico.config(image=icon_img)
            else:
                ico.config(fg=TEXT_DIM)

        def _hover_on(e):
            if self.active_page != page_key:
                self._animate_bg(all_widgets, BG_SIDEBAR, BG_HOVER, steps=6, delay=8)
            self._show_tip(ico, tooltip)

        def _hover_off(e):
            if self.active_page != page_key:
                self._animate_bg(all_widgets, BG_HOVER, BG_SIDEBAR, steps=6, delay=8)
            self._hide_tip()

        def _click(e):
            self._animate_bg(all_widgets, BG_HOVER, ACTIVE_BG, steps=5, delay=7)
            _anim_bg(bar, BG_SIDEBAR, "#ffffff", steps=3, delay=5)
            _ANIM_ROOT.after(60, lambda: _anim_bg(bar, "#ffffff", ACTIVE_BAR, steps=6, delay=8))
            self._navigate(page_key)

        for w in [outer, inner, ico, lbl_w, bar]:
            w.bind("<Enter>", _hover_on)
            w.bind("<Leave>", _hover_off)
            w.bind("<Button-1>", _click)

        outer._activate   = _activate
        outer._deactivate = _deactivate

    def _nav_btn(self, parent, icon, tooltip, key):
        """Legacy fallback nav btn for non-icon items (save/webhook)."""
        b = tk.Label(parent, text=icon, bg=BG_SIDEBAR, fg=TEXT_FAINT,
                     font=("Segoe UI", 12), width=3, cursor="hand2", anchor="center",
                     padx=4, pady=6, highlightthickness=0, relief="flat")
        def enter(e):
            if self.active_page != key:
                b.config(bg=BG_HOVER, fg=TEXT_DIM)
            self._show_tip(b, tooltip)
        def leave(e):
            if self.active_page != key:
                b.config(bg=BG_SIDEBAR, fg=TEXT_FAINT)
            self._hide_tip()
        def click(e):
            if key in ("save_config", "test_hooks"):
                self._action(key)
            else:
                self._navigate(key)
        b.bind("<Enter>", enter)
        b.bind("<Leave>", leave)
        b.bind("<Button-1>", click)
        return b

    def _navigate(self, key):
        builders = {
            "dashboard":     self._page_dashboard,
            "webhooks":      self._page_webhooks,
            "biome_actions": self._page_biome_actions,
            "launch":        self._page_launch,
            "antiafk":       self._page_antiafk,
            "activity":      self._page_activity,
            "accounts":      self._page_accounts,
        }
        if key not in builders or key == self.active_page:
            return
        if getattr(self, "_transitioning", False):
            return

        prev_key  = self.active_page
        prev_page = self._page_cache.get(prev_key) if prev_key else None

        if prev_key:
            old_frame = getattr(self, "_nav_btn_frames", {}).get(prev_key)
            if old_frame and hasattr(old_frame, "_deactivate"):
                old_frame._deactivate()
        new_frame = getattr(self, "_nav_btn_frames", {}).get(key)
        if new_frame and hasattr(new_frame, "_activate"):
            new_frame._activate()
        else:
            new_btn = self._nav_btns.get(key)
            if new_btn:
                try: new_btn.config(bg=ACCENT_DIM, fg=ACCENT)
                except Exception: pass

        self.active_page = key
        self._dash_alive = (key == "dashboard")

        if key not in self._page_cache:
            page = builders[key](self._content)
            page.grid(row=0, column=0, sticky="nsew")
            page.grid_remove()
            self._page_cache[key] = page

        incoming = self._page_cache[key]

        if key == "dashboard":
            try: self._refresh_log_frame()
            except Exception: pass
            try: self._refresh_instance_chips()
            except Exception: pass
        if key == "webhooks":
            try: self._wh_refresh_list()
            except Exception: pass

        if prev_page and _ANIM_ROOT:
            self._slide_transition(incoming, prev_page)
        else:
            if prev_page:
                try: prev_page.grid_remove()
                except Exception: pass
            incoming.grid(row=0, column=0, sticky="nsew")

    def _build_page_async(self, key, builder, callback):
        """Unused — pages are pre-built by _prebuild_pages."""
        pass

    def _fade_out_page(self, page, callback=None, *a, **kw):
        if callback: callback()

    def _fade_in_page(self, page, *a, **kw):
        pass

    def _slide_transition(self, incoming, outgoing):
        """
        Crossfade: incoming page appears with a canvas overlay that fades from
        BG_BASE → transparent, giving a clean visible fade-in with zero layout lag.
        """
        if getattr(self, "_transitioning", False):
            try: outgoing.grid_remove()
            except Exception: pass
            incoming.grid(row=0, column=0, sticky="nsew")
            return

        self._transitioning = True

        try:
            outgoing.grid_remove()
            incoming.grid(row=0, column=0, sticky="nsew")
            incoming.update_idletasks()
        except Exception:
            self._transitioning = False
            return

        W = incoming.winfo_width()
        H = incoming.winfo_height()
        if W < 10 or H < 10:
            self._transitioning = False
            return

        overlay = tk.Canvas(incoming, width=W, height=H,
                            bg=BG_BASE, highlightthickness=0, bd=0)
        overlay.place(x=0, y=0, width=W, height=H)

        STEPS = 10
        DELAY = 18

        def _fade(step=0):
            if step > STEPS:
                try: overlay.destroy()
                except Exception: pass
                self._transitioning = False
                return
            stipples = ["", "gray12", "gray25", "gray50", "gray75",
                        "gray75", "gray50", "gray25", "gray12", "", ""]
            t = step / STEPS
            try:
                overlay.delete("fade")
                if step < len(stipples) - 1:
                    stip = stipples[step]
                    if stip:
                        overlay.create_rectangle(0, 0, W, H,
                            fill=BG_BASE, stipple=stip, outline="", tags="fade")
                    else:
                        overlay.config(bg=BG_BASE if step == 0 else "")
            except Exception:
                pass
            if step == 0:
                overlay.config(bg=BG_BASE)
            elif step >= STEPS - 2:
                try: overlay.destroy()
                except Exception: pass
                self._transitioning = False
                return
            _ANIM_ROOT.after(DELAY, lambda: _fade(step + 1))

        _fade(0)

    def _action(self, key):
        if key == "save_config":
            self._save_config()
            self._toast("💾  Config saved!")
        elif key == "test_hooks":
            self._send_test_webhook()


    def _page_dashboard(self, parent):
        page = fr(parent, bg=BG_BASE)
        page.columnconfigure(0, weight=1)
        page.rowconfigure(0, weight=1)

        sf = ScrollFrame(page, bg=BG_BASE)
        sf.grid(row=0, column=0, sticky="nsew")
        inn = sf.inner
        inn.columnconfigure(0, weight=1)

        row0 = fr(inn, bg=BG_BASE)
        row0.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 0))
        row0.columnconfigure(0, weight=1)
        row0.columnconfigure(1, weight=1)

        sc = card(row0)
        sc.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        sc.columnconfigure(1, weight=1)

        pulse_cv = tk.Canvas(sc, width=14, height=14, bg=BG_CARD,
                             highlightthickness=0, bd=0)
        pulse_cv.create_oval(3, 3, 11, 11, fill=RED, outline="", tags="dot")
        pulse_cv.grid(row=0, column=0, rowspan=2, padx=(12, 6), pady=12)
        self._pulse_cv = pulse_cv
        self._animate_pulse(pulse_cv)

        self._status_lbl = lbl(sc, "Stopped", fg=TEXT_DIM, bg=BG_CARD,
                               font=("Segoe UI", 12, "bold"), anchor="sw")
        self._status_lbl.grid(row=0, column=1, sticky="sw", pady=(12, 0))
        self._status_sub = lbl(sc, "Press F8 to start", fg=TEXT_FAINT, bg=BG_CARD,
                               font=("Segoe UI", 8), anchor="nw")
        self._status_sub.grid(row=1, column=1, sticky="nw", pady=(0, 12))

        btn_wrap = fr(sc, bg=BG_CARD)
        btn_wrap.grid(row=0, column=2, rowspan=2, padx=(0, 12))
        f8 = lbl(btn_wrap, "F8", fg=TEXT_FAINT, bg=BG_ITEM,
                 font=("Segoe UI", 7, "bold"), padx=4, pady=2)
        f8.pack(side="left", padx=(0, 6))
        self._play_cv = tk.Canvas(btn_wrap, width=32, height=32, bg=BG_CARD,
                                  highlightthickness=0, bd=0, cursor="hand2")
        self._play_cv.create_rectangle(0, 0, 32, 32, fill=RED, outline="", tags="bg")
        self._play_cv.create_polygon(11, 8, 23, 16, 11, 24, fill="#ffffff", tags="icon")
        self._play_cv.pack(side="left")
        self._play_cv.bind("<Button-1>", lambda e: self._toggle_macro())
        self._play_cv.bind("<Enter>",
            lambda e=None: self._play_cv.itemconfig("bg",
                fill=RED_HOVER if not self.running else ACCENT_HOVER))
        self._play_cv.bind("<Leave>",
            lambda e=None: self._play_cv.itemconfig("bg",
                fill=RED if not self.running else ACCENT))

        tc = card(row0)
        tc.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        lbl(tc, "Macro Time", fg=TEXT_FAINT, bg=BG_CARD,
            font=("Segoe UI", 8)).pack(anchor="w", padx=12, pady=(12, 2))
        self._timer_lbl = lbl(tc, "00:00:00", fg=ACCENT, bg=BG_CARD,
                              font=("Consolas", 20, "bold"))
        self._timer_lbl.pack(anchor="w", padx=12, pady=(0, 4))

        chips_row = fr(tc, bg=BG_CARD)
        chips_row.pack(anchor="w", padx=12, pady=(0, 10))
        self._inst_chip = lbl(chips_row, f"{len(self.accounts)} accounts", fg=TEXT_DIM, bg=BG_CARD,
                              font=("Segoe UI", 8))
        self._inst_chip.pack(side="left")
        self._active_chip = lbl(chips_row, "  0 active", fg=ACCENT, bg=ACCENT_DIM,
                                font=("Segoe UI", 7, "bold"), padx=5, pady=1)
        self._active_chip.pack(side="left", padx=(6, 0))

        ac = card(inn)
        ac.grid(row=1, column=0, sticky="ew", padx=12, pady=(8, 0))
        ah = fr(ac, bg=BG_CARD)
        ah.pack(fill="x", padx=12, pady=(8, 4))
        lbl(ah, "ACTIVE ACCOUNTS", fg=TEXT_FAINT, bg=BG_CARD,
            font=("Segoe UI", 8, "bold")).pack(side="left")
        self._online_badge = lbl(ah, "0 online", fg=ACCENT, bg=ACCENT_DIM,
                                 font=("Segoe UI", 7, "bold"), padx=5, pady=1)
        self._online_badge.pack(side="right")
        self._log_frame = fr(ac, bg=BG_CARD)
        self._log_frame.pack(fill="x", padx=12, pady=(0, 10))
        self._refresh_log_frame()

        bc = card(inn)
        bc.grid(row=2, column=0, sticky="ew", padx=12, pady=(8, 0))
        bh = fr(bc, bg=BG_CARD)
        bh.pack(fill="x", padx=12, pady=(8, 4))
        lbl(bh, "BIOME COUNTS", fg=TEXT_FAINT, bg=BG_CARD,
            font=("Segoe UI", 8, "bold")).pack(side="left")
        reset_btn = lbl(bh, "Reset", fg=TEXT_FAINT, bg=BG_CARD,
                        font=("Segoe UI", 7), cursor="hand2")
        reset_btn.pack(side="right")
        reset_btn.bind("<Button-1>", lambda e: self._reset_biome_counts())
        reset_btn.bind("<Enter>", lambda e: reset_btn.config(fg=RED))
        reset_btn.bind("<Leave>", lambda e: reset_btn.config(fg=TEXT_FAINT))

        grid = fr(bc, bg=BG_CARD)
        grid.pack(fill="x", padx=10, pady=(4, 12))
        self._biome_count_labels = {}
        cols = 5
        for i, (name, color, *_) in enumerate(BIOMES):
            biome_info = BIOME_DATA.get(name, {})
            emoji      = biome_info.get("emoji", "")
            ci, ri = i % cols, i // cols
            grid.columnconfigure(ci, weight=1, uniform="biome")

            cell = tk.Frame(grid, bg=BG_ITEM, bd=0,
                            highlightthickness=1, highlightbackground=BORDER_ITEM,
                            cursor="hand2")
            cell.grid(row=ri, column=ci, padx=4, pady=4, sticky="ew", ipady=4)

            dot_cv = tk.Canvas(cell, width=8, height=8, bg=BG_ITEM,
                               highlightthickness=0)
            dot_cv.create_oval(1,1,7,7, fill=color, outline="", tags="d")
            dot_cv.pack(side="left", padx=(8,3), pady=0)

            name_frame = tk.Frame(cell, bg=BG_ITEM)
            name_frame.pack(side="left", fill="x", expand=True)

            short = name if len(name) <= 7 else name[:7]
            tk.Label(name_frame, text=emoji, bg=BG_ITEM, fg=TEXT_DIM,
                     font=("Segoe UI", 9)).pack(side="left", padx=(0,2))
            tk.Label(name_frame, text=short.upper(), bg=BG_ITEM, fg=TEXT_DIM,
                     font=("Segoe UI", 7, "bold"), anchor="w").pack(side="left")

            count = self.biome_counts.get(name, 0)
            ct = tk.Label(cell, text=str(count),
                          fg=ACCENT if count > 0 else TEXT_FAINTEST,
                          bg=BG_ITEM, font=("Segoe UI", 10, "bold"), padx=8)
            ct.pack(side="right")
            self._biome_count_labels[name] = ct

            _cell_widgets = [cell, name_frame, dot_cv, ct] + name_frame.winfo_children()
            def _on_enter(e, c=cell, ws=[cell, name_frame, ct]):
                _anim_border(c, BORDER_ITEM, ACCENT, steps=6, delay=8)
                for w in ws:
                    _anim_bg(w, BG_ITEM, BG_HOVER, steps=6, delay=8)
            def _on_leave(e, c=cell, ws=[cell, name_frame, ct]):
                _anim_border(c, ACCENT, BORDER_ITEM, steps=6, delay=8)
                for w in ws:
                    _anim_bg(w, BG_HOVER, BG_ITEM, steps=6, delay=8)
            for w in [cell, name_frame]:
                w.bind("<Enter>", _on_enter)
                w.bind("<Leave>", _on_leave)

        act = fr(inn, bg=BG_BASE)
        act.grid(row=3, column=0, sticky="ew", padx=12, pady=8)
        act.columnconfigure(0, weight=1)
        act.columnconfigure(1, weight=1)

        start_b = accent_btn(act, "▶  Start  (F8)", command=self._on_start,
                             font=("Segoe UI", 10, "bold"))
        start_b.grid(row=0, column=0, sticky="ew", padx=(0, 5), ipady=6)
        stop_b  = red_btn(act, "■  Stop", command=self._on_stop)
        stop_b.grid(row=0, column=1, sticky="ew", padx=(5, 0), ipady=6)
        stop_b.config(font=("Segoe UI", 10, "bold"))
        self._start_btn = start_b
        self._stop_btn  = stop_b

        foot = fr(inn, bg=BG_BASE)
        foot.grid(row=4, column=0, sticky="ew", padx=12, pady=(4, 12))
        foot.columnconfigure(0, weight=1)

        dev_row = fr(foot, bg=BG_BASE)
        dev_row.pack(side="left")

        av_cv = tk.Canvas(dev_row, width=22, height=22, bg=BG_BASE,
                          highlightthickness=0, bd=0)
        av_cv.create_oval(1, 1, 21, 21, fill=ACCENT_DIM, outline=ACCENT, tags="bg")
        av_cv.create_text(11, 11, text="P", fill=TEXT_PRIMARY,
                          font=("Segoe UI", 8, "bold"), tags="ph")
        av_cv.pack(side="left", padx=(0, 5))

        def _load_dev_avatar():
            photo = _load_embedded_image(_PWS32Z_AVATAR_B64, 22)
            if photo:
                self._dev_avatar_photo = photo
                def _draw():
                    try:
                        av_cv.delete("all")
                        av_cv.create_image(0, 0, anchor="nw", image=photo)
                    except Exception:
                        pass
                self.root.after(0, _draw)
        threading.Thread(target=_load_dev_avatar, daemon=True).start()

        dev = lbl(dev_row, "pws32z", fg=TEXT_DIM, bg=BG_BASE,
                  font=("Segoe UI", 8, "bold"), cursor="hand2")
        dev.pack(side="left")
        dev.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/pws32z"))
        dev.bind("<Enter>", lambda e: _anim_fg(dev, TEXT_DIM, ACCENT))
        dev.bind("<Leave>", lambda e: _anim_fg(dev, ACCENT, TEXT_DIM))
        av_cv.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/pws32z"))
        av_cv.bind("<Enter>", lambda e: _anim_fg(dev, TEXT_DIM, ACCENT))
        av_cv.bind("<Leave>", lambda e: _anim_fg(dev, ACCENT, TEXT_DIM))

        lbl(foot, "  ·  Forked from MultiScope-V1 by @cresqent",
            fg=TEXT_FAINT, bg=BG_BASE,
            font=("Segoe UI", 7)).pack(side="left")

        help_row = fr(foot, bg=BG_BASE)
        help_row.pack(side="right")

        lbl(help_row, "Need Help?  ", fg=TEXT_DIM, bg=BG_BASE,
            font=("Segoe UI", 8)).pack(side="left")

        disc_cv = tk.Canvas(help_row, width=22, height=22, bg=BG_BASE,
                            highlightthickness=0, bd=0, cursor="hand2")
        disc_cv.pack(side="left", padx=(0, 2))

        def _load_disc_icon():
            photo = _load_embedded_image(_DISCORD_PNG_B64, 22)
            if photo:
                self._disc_icon_photo = photo
                def _draw():
                    try:
                        disc_cv.delete("all")
                        disc_cv.create_image(0, 0, anchor="nw", image=photo)
                    except Exception:
                        pass
                self.root.after(0, _draw)
            else:
                disc_lbl = lbl(help_row, "Join Discord", fg=DISCORD_COLOR, bg=BG_BASE,
                               font=("Segoe UI", 8), cursor="hand2")
                disc_lbl.pack(side="left")
                disc_lbl.bind("<Button-1>", lambda e: webbrowser.open("https://discord.gg/sBvTjBNzeS"))
        threading.Thread(target=_load_disc_icon, daemon=True).start()

        def _disc_click(e): webbrowser.open("https://discord.gg/sBvTjBNzeS")
        def _disc_enter(e):
            try: disc_cv.config(bg="#3b3f8f")
            except Exception: pass
        def _disc_leave(e):
            try: disc_cv.config(bg=BG_BASE)
            except Exception: pass
        disc_cv.bind("<Button-1>", _disc_click)
        disc_cv.bind("<Enter>",    _disc_enter)
        disc_cv.bind("<Leave>",    _disc_leave)

        self._dash_alive = True
        self._tick_timer()
        self._refresh_instance_chips()
        self._apply_running_state_to_dashboard()
        return page

    def _apply_running_state_to_dashboard(self):
        try:
            if self.running:
                self._status_lbl.config(text="Active", fg=ACCENT)
                self._status_sub.config(text="Monitoring biomes…")
                self._pulse_cv.itemconfig("dot", fill=ACCENT)
                self._play_cv.delete("icon")
                self._play_cv.create_rectangle(9, 8, 14, 23, fill="#ffffff", tags="icon")
                self._play_cv.create_rectangle(18, 8, 23, 23, fill="#ffffff", tags="icon")
                self._play_cv.itemconfig("bg", fill=ACCENT)
                self._play_cv.bind("<Enter>",
                    lambda e=None: self._play_cv.itemconfig("bg", fill=ACCENT_HOVER))
                self._play_cv.bind("<Leave>",
                    lambda e=None: self._play_cv.itemconfig("bg", fill=ACCENT))
                if self.macro_start:
                    elapsed = int(time.time() - self.macro_start)
                    self._timer_lbl.config(
                        text=f"{elapsed//3600:02d}:{(elapsed%3600)//60:02d}:{elapsed%60:02d}")
        except Exception:
            pass
        try:
            if self.running:
                self._topbar_status_pill.config(bg=ACCENT_DIM,
                    highlightthickness=1, highlightbackground=ACCENT)
                self._topbar_status_dot.config(bg=ACCENT_DIM)
                self._topbar_status_dot.itemconfig("d", fill=ACCENT)
                self._topbar_status_lbl.config(text="Active", fg=ACCENT, bg=ACCENT_DIM)
                self._sb_dot_cv.itemconfig("dot", fill=ACCENT)
            else:
                self._topbar_status_pill.config(bg=RED_BG,
                    highlightthickness=1, highlightbackground="#3a1520")
                self._topbar_status_dot.config(bg=RED_BG)
                self._topbar_status_dot.itemconfig("d", fill=RED)
                self._topbar_status_lbl.config(text="Stopped", fg=RED, bg=RED_BG)
                self._sb_dot_cv.itemconfig("dot", fill=TEXT_FAINTEST)
        except Exception:
            pass

    def _page_instances(self, parent):
        page = fr(parent, bg=BG_BASE)
        page.columnconfigure(0, weight=1)
        page.rowconfigure(1, weight=1)

        hdr = fr(page, bg=BG_BASE)
        hdr.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))
        lbl(hdr, "Instances", fg=TEXT_PRIMARY, bg=BG_BASE,
            font=("Segoe UI", 14, "bold")).pack(side="left")
        self._inst_count_badge = lbl(hdr, f"  {len(self.instances)}  ",
                                     fg=ACCENT, bg=ACCENT_DIM,
                                     font=("Segoe UI", 7, "bold"), padx=6, pady=2)
        self._inst_count_badge.pack(side="left", padx=6)

        sf = ScrollFrame(page, bg=BG_BASE)
        sf.grid(row=1, column=0, sticky="nsew", padx=12)
        self._inst_sf   = sf
        self._inst_inner = sf.inner
        self._inst_inner.columnconfigure(0, weight=1)
        self._refresh_instance_list()

        btn_row = fr(page, bg=BG_BASE)
        btn_row.grid(row=2, column=0, padx=12, pady=8, sticky="w")

        accent_btn(btn_row, "＋  Add Instance", command=self._add_instance,
                   padx=10, pady=5).pack(side="left", padx=(0, 8))
        icon_btn(btn_row, "⟳  Scan (F5)", command=self._scan_instances).pack(
            side="left", padx=(0, 8))
        icon_btn(btn_row, "💾  Save All", command=self._save_all_instances).pack(
            side="left")

        return page

    def _refresh_instance_list(self):
        for w in self._inst_inner.winfo_children():
            w.destroy()
        if not self.instances:
            lbl(self._inst_inner,
                "No instances yet. Click '+ Add Instance' or use the Launch tab.",
                fg=TEXT_FAINT, bg=BG_BASE, font=("Segoe UI", 8),
                pady=24).pack(padx=12)
            return
        for inst in self.instances:
            self._build_instance_card(self._inst_inner, inst)
        try:
            self._inst_count_badge.config(text=f"  {len(self.instances)}  ")
        except Exception:
            pass

    def _build_instance_card(self, parent, inst):
        sf = getattr(self, "_inst_sf", None)

        outer = tk.Frame(parent, bg=BG_CARD, bd=0,
                         highlightthickness=1, highlightbackground=BORDER)
        outer.pack(fill="x", pady=4)
        outer.columnconfigure(0, weight=1)

        hdr_row = fr(outer, bg=BG_ITEM)
        hdr_row.pack(fill="x")
        hdr_row.config(highlightthickness=1, highlightbackground=BORDER_ITEM)

        arrow_lbl = lbl(hdr_row, "▶", fg=TEXT_FAINT, bg=BG_ITEM,
                        font=("Segoe UI", 8), cursor="hand2")
        arrow_lbl.pack(side="left", padx=(8, 4), pady=8)

        av_cv = tk.Canvas(hdr_row, width=28, height=28, bg=BG_ITEM,
                          highlightthickness=0, bd=0)
        av_cv.create_rectangle(0, 0, 28, 28, fill=BG_CARD, outline=BORDER)
        av_cv.create_text(14, 14, text="?", fill=TEXT_FAINT,
                          font=("Segoe UI", 9, "bold"), tags="ph")
        av_cv.pack(side="left", padx=(0, 8), pady=5)
        inst["_av_cv"] = av_cv
        uname = inst.get("roblox_username", "").strip()
        if uname:
            threading.Thread(target=self._load_avatar_small,
                             args=(inst, av_cv, 28), daemon=True).start()

        id_lbl = lbl(hdr_row, f"Instance #{inst['id']}", fg=ACCENT, bg=BG_ITEM,
                     font=("Segoe UI", 9, "bold"))
        id_lbl.pack(side="left")
        uname_d = inst.get("roblox_username") or "No username"
        lbl(hdr_row, f"  —  {uname_d}", fg=TEXT_MUTED, bg=BG_ITEM,
            font=("Segoe UI", 8)).pack(side="left")

        right_f = fr(hdr_row, bg=BG_ITEM)
        right_f.pack(side="right", padx=8)

        wh = inst.get("discord_webhook", "").strip()
        hook_ind = lbl(right_f, "⚡ Webhook" if wh else "⚡ No webhook",
                       fg=ACCENT if wh else TEXT_FAINT, bg=BG_ITEM,
                       font=("Segoe UI", 7))
        hook_ind.pack(side="right", padx=(6, 0))

        status_color = ACCENT if inst.get("active") else TEXT_FAINT
        status_sym   = "●" if inst.get("active") else "○"
        status_ind = lbl(right_f, status_sym, fg=status_color, bg=BG_ITEM,
                         font=("Segoe UI", 10))
        status_ind.pack(side="right")

        body = fr(outer, bg=BG_CARD)
        visible = [False]
        _last_inst_toggle = [0.0]

        def toggle(_e=None):
            import time as _ti
            now = _ti.monotonic()
            if now - _last_inst_toggle[0] < 0.35:
                return "break"
            _last_inst_toggle[0] = now
            if visible[0]:
                body.pack_forget()
                arrow_lbl.config(text="▶")
                visible[0] = False
            else:
                body.pack(fill="x")
                arrow_lbl.config(text="▼")
                visible[0] = True
            return "break"

        for w in [hdr_row, arrow_lbl, id_lbl]:
            w.bind("<Button-1>", toggle)

        def field(label_text, var_key, default_key):
            rf = fr(body, bg=BG_CARD)
            rf.pack(fill="x", padx=12, pady=(8, 0))
            lbl(rf, label_text, fg=TEXT_FAINT, bg=BG_CARD,
                font=("Segoe UI", 8)).pack(anchor="w")
            if var_key not in inst:
                inst[var_key] = tk.StringVar(value=inst.get(default_key, ""))
            e = styled_entry(rf, textvariable=inst[var_key])
            e.pack(fill="x", ipady=4, pady=(2, 0))
            if sf:
                sf.bind_mousewheel(e)
            return e

        field("Roblox Username", "roblox_username_var", "roblox_username")
        field("Private Server Link  (used as 'Join Server' in alerts)",
              "private_server_var", "private_server")
        wh_entry = field("Discord Webhook URL (per-instance)",
                         "discord_webhook_var", "discord_webhook")

        btn_f = fr(body, bg=BG_CARD)
        btn_f.pack(fill="x", padx=12, pady=(8, 10))

        def save_inst():
            inst["roblox_username"] = inst["roblox_username_var"].get().strip()
            inst["private_server"]  = inst["private_server_var"].get().strip()
            inst["discord_webhook"] = inst["discord_webhook_var"].get().strip()
            wh_now = inst["discord_webhook"]
            hook_ind.config(text="⚡ Webhook" if wh_now else "⚡ No webhook",
                            fg=ACCENT if wh_now else TEXT_FAINT)
            if inst["roblox_username"]:
                threading.Thread(target=self._load_avatar_small,
                                 args=(inst, inst.get("_av_cv"), 28),
                                 daemon=True).start()
            self._save_config()
            self._toast(f"✓  Instance #{inst['id']} saved")

        def stop_inst():
            inst["active"] = False
            status_ind.config(text="○", fg=TEXT_FAINT)
            self._log_activity(f"■ Instance #{inst['id']} stopped manually")
            self._toast(f"■  Instance #{inst['id']} stopped")

        def remove_inst():
            self.instances = [i for i in self.instances if i["id"] != inst["id"]]
            self._save_config()
            self._refresh_instance_list()
            self._log_activity(f"✕ Instance #{inst['id']} removed")
            self._toast(f"✕  Instance #{inst['id']} removed")

        accent_btn(btn_f, "Save", command=save_inst, padx=12, pady=4).pack(
            side="left", padx=(0, 6))

        def _join_server():
            link = inst.get("private_server_var", tk.StringVar()).get().strip() \
                   or inst.get("private_server", "").strip()
            if link:
                webbrowser.open(link)
            else:
                self._toast("⚠  No private server link set")

        icon_btn(btn_f, "🔗 Join Server",
                 command=_join_server,
                 padx=8, pady=4).pack(side="left", padx=(0, 6))

        icon_btn(btn_f, "■ Stop", fg=RED, bg=RED_BG, hover_fg=RED,
                 hover_bg=RED_HOVER, command=stop_inst,
                 padx=10, pady=4).pack(side="left", padx=(0, 6))
        icon_btn(btn_f, "✕ Remove", fg=TEXT_FAINT, bg=BG_ITEM,
                 hover_fg=RED, hover_bg=RED_BG,
                 command=remove_inst, padx=10, pady=4).pack(side="left")

    def _add_instance(self):
        new_id = max((i["id"] for i in self.instances), default=0) + 1
        self.instances.append({
            "id": new_id,
            "roblox_username": "",
            "private_server":  "",
            "discord_webhook": "",
            "active": False,
        })
        self._refresh_instance_list()
        self._toast(f"＋  Instance #{new_id} added")
        self._log_activity(f"＋ Instance #{new_id} added")

    def _save_all_instances(self):
        for inst in self.instances:
            for var_key, data_key in [
                ("roblox_username_var", "roblox_username"),
                ("private_server_var",  "private_server"),
                ("discord_webhook_var", "discord_webhook"),
            ]:
                if var_key in inst:
                    inst[data_key] = inst[var_key].get().strip()
        self._save_config()
        self._toast("💾  All instances saved")

    def _page_antiafk(self, parent):
        page = fr(parent, bg=BG_BASE)
        page.columnconfigure(0, weight=1)
        page.rowconfigure(1, weight=1)

        lbl(page, "Anti-AFK", fg=TEXT_PRIMARY, bg=BG_BASE,
            font=("Segoe UI", 14, "bold")).grid(row=0, column=0, sticky="w",
                                                padx=12, pady=(12, 4))
        sf = ScrollFrame(page, bg=BG_BASE)
        sf.grid(row=1, column=0, sticky="nsew")
        inn = sf.inner
        inn.columnconfigure(0, weight=1)

        sc = card(inn)
        sc.grid(row=0, column=0, sticky="ew", padx=12, pady=(8, 4))
        sh = fr(sc, bg=BG_CARD)
        sh.pack(fill="x", padx=12, pady=(10, 4))
        lbl(sh, "STATUS", fg=TEXT_FAINT, bg=BG_CARD,
            font=("Segoe UI", 8, "bold")).pack(side="left")
        self._afk_status_lbl = lbl(sh,
            "● Running" if self._antiafk_running else "○ Stopped",
            fg=ACCENT if self._antiafk_running else TEXT_FAINT,
            bg=BG_CARD, font=("Segoe UI", 8, "bold"))
        self._afk_status_lbl.pack(side="right")

        win_row = fr(sc, bg=BG_CARD)
        win_row.pack(fill="x", padx=12, pady=(0, 6))
        lbl(win_row, "Roblox windows detected:", fg=TEXT_FAINT, bg=BG_CARD,
            font=("Segoe UI", 8)).pack(side="left")
        self._afk_win_count_lbl = lbl(win_row, "—", fg=ACCENT, bg=BG_CARD,
                                       font=("Segoe UI", 8, "bold"))
        self._afk_win_count_lbl.pack(side="left", padx=(6, 0))

        if not WIN32_AVAILABLE:
            lbl(sc, "⚠  pywin32 + psutil not installed.  Run:  pip install pywin32 psutil",
                fg=WARN, bg=BG_CARD, font=("Segoe UI", 8),
                justify="left", wraplength=500).pack(anchor="w", padx=12, pady=(0, 8))

        cfg_c = card(inn)
        cfg_c.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 4))
        lbl(cfg_c, "ACTION SETTINGS", fg=TEXT_FAINT, bg=BG_CARD,
            font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=12, pady=(10, 4))

        rows_f = fr(cfg_c, bg=BG_CARD)
        rows_f.pack(fill="x", padx=12, pady=(0, 10))

        def setting_row(label_text, widget_fn):
            r = fr(rows_f, bg=BG_CARD)
            r.pack(fill="x", pady=3)
            if label_text:
                lbl(r, label_text, fg=TEXT_MUTED, bg=BG_CARD,
                    font=("Segoe UI", 9), width=26, anchor="w").pack(side="left")
            widget_fn(r)

        def _make_interval(p):
            styled_entry(p, textvariable=self._antiafk_interval, width=6
                         ).pack(side="left", ipady=3)
            lbl(p, "  sec", fg=TEXT_FAINT, bg=BG_CARD, font=("Segoe UI", 8)).pack(side="left")
            for secs, t in [(60, "1m"), (120, "2m"), (300, "5m"), (600, "10m")]:
                icon_btn(p, t, padx=5, pady=2,
                         command=lambda s=secs: self._antiafk_interval.set(s)
                         ).pack(side="left", padx=2)
        setting_row("Interval (seconds)", _make_interval)

        def _make_action(p):
            cb = ttk.Combobox(p, textvariable=self._antiafk_action,
                              values=["click", "click+space", "space", "ws", "zoom"],
                              width=16, state="readonly")
            cb.pack(side="left", ipady=2)
            lbl(p, "  click = left-click inside game, no focus steal",
                fg=TEXT_FAINT, bg=BG_CARD, font=("Segoe UI", 7)).pack(side="left", padx=(6,0))
        setting_row("Action type", _make_action)

        self._afk_click_x_pct  = tk.IntVar(value=50)
        self._afk_click_y_pct  = tk.IntVar(value=50)
        self._afk_click_hold_ms = tk.IntVar(value=80)

        def _make_click_pos(p):
            lbl(p, "X%:", fg=TEXT_FAINT, bg=BG_CARD, font=("Segoe UI", 8)).pack(side="left")
            styled_entry(p, textvariable=self._afk_click_x_pct, width=4
                         ).pack(side="left", ipady=3, padx=(2, 8))
            lbl(p, "Y%:", fg=TEXT_FAINT, bg=BG_CARD, font=("Segoe UI", 8)).pack(side="left")
            styled_entry(p, textvariable=self._afk_click_y_pct, width=4
                         ).pack(side="left", ipady=3, padx=(2, 0))
            lbl(p, "  (50 50 = centre, 0 0 = top-left, 100 100 = bottom-right)",
                fg=TEXT_FAINT, bg=BG_CARD, font=("Segoe UI", 7)).pack(side="left", padx=(6,0))
        setting_row("Click position (%)", _make_click_pos)

        def _make_hold(p):
            styled_entry(p, textvariable=self._afk_click_hold_ms, width=5
                         ).pack(side="left", ipady=3)
            lbl(p, "  ms hold  (50–200 recommended)",
                fg=TEXT_FAINT, bg=BG_CARD, font=("Segoe UI", 7)).pack(side="left")
        setting_row("Click hold (ms)", _make_hold)

        def _make_userafe(p):
            styled_check(p, variable=self._antiafk_user_safe,
                         bg=BG_CARD).pack(side="left")
            lbl(p, "True-AFK mode — wait until YOU go idle first",
                fg=TEXT_FAINT, bg=BG_CARD, font=("Segoe UI", 8)).pack(side="left")
        setting_row("", _make_userafe)

        def _make_seq(p):
            styled_check(p, variable=self._antiafk_sequential,
                         bg=BG_CARD).pack(side="left")
            lbl(p, "Sequential mode  (stagger across instances)",
                fg=TEXT_FAINT, bg=BG_CARD, font=("Segoe UI", 8)).pack(side="left")
        setting_row("", _make_seq)

        def _make_seqdel(p):
            styled_entry(p, textvariable=self._antiafk_seq_delay, width=6
                         ).pack(side="left", ipady=3)
            lbl(p, "  sec between each window",
                fg=TEXT_FAINT, bg=BG_CARD, font=("Segoe UI", 8)).pack(side="left")
        setting_row("Sequential delay", _make_seqdel)

        btn_f = fr(inn, bg=BG_BASE)
        btn_f.grid(row=2, column=0, padx=12, pady=6, sticky="w")
        accent_btn(btn_f, "▶  Start  (F9)",
                   command=lambda: self._set_antiafk(True),
                   padx=12, pady=5).pack(side="left", padx=(0, 8))
        red_btn(btn_f, "■  Stop",
                command=lambda: self._set_antiafk(False),
                padx=12, pady=5).pack(side="left", padx=(0, 8))
        icon_btn(btn_f, "▶ Test Click", command=self._afk_test_action,
                 padx=10, pady=5).pack(side="left", padx=(0, 8))
        if WIN32_AVAILABLE:
            icon_btn(btn_f, "□ Show Roblox", command=self._afk_show_windows,
                     padx=10, pady=5).pack(side="left", padx=(0, 8))
            icon_btn(btn_f, "■ Hide Roblox", command=self._afk_hide_windows,
                     fg=RED, bg=RED_BG, hover_fg=RED, hover_bg=RED_HOVER,
                     padx=10, pady=5).pack(side="left")

        wic = card(inn)
        wic.grid(row=3, column=0, sticky="ew", padx=12, pady=(4, 4))
        wih = fr(wic, bg=BG_CARD)
        wih.pack(fill="x", padx=12, pady=(8, 4))
        lbl(wih, "ROBLOX WINDOWS", fg=TEXT_FAINT, bg=BG_CARD,
            font=("Segoe UI", 8, "bold")).pack(side="left")
        rb = lbl(wih, "↻ Refresh", fg=TEXT_FAINT, bg=BG_CARD,
                 font=("Segoe UI", 7), cursor="hand2")
        rb.pack(side="right")
        win_list_frame = fr(wic, bg=BG_CARD)
        win_list_frame.pack(fill="x", padx=12, pady=(0, 10))
        self._afk_win_list_frame = win_list_frame
        self._afk_refresh_window_list(win_list_frame)
        rb.bind("<Button-1>", lambda e: self._afk_refresh_window_list(win_list_frame))
        rb.bind("<Enter>", lambda e: rb.config(fg=ACCENT))
        rb.bind("<Leave>", lambda e: rb.config(fg=TEXT_FAINT))

        info_c = card(inn)
        info_c.grid(row=4, column=0, sticky="ew", padx=12, pady=(0, 12))
        lbl(info_c,
            "ℹ  Anti-AFK uses PostMessage to send clicks/keypresses directly into Roblox "
            "windows without stealing your focus or moving your mouse. "
            "'click' sends a left-click at the configured X/Y% position inside the game. "
            "'click+space' clicks then presses Space. Requires pywin32 + psutil.",
            fg=TEXT_FAINT, bg=BG_CARD, font=("Segoe UI", 8),
            wraplength=540, justify="left").pack(anchor="w", padx=12, pady=10)

        self._afk_tick_window_count()
        return page
    def _toggle_antiafk(self):
        self._set_antiafk(not self._antiafk_running)

    def _set_antiafk(self, enable):
        if enable and not self._antiafk_running:
            self._start_antiafk()
        elif not enable and self._antiafk_running:
            self._stop_antiafk()
        self._update_afk_status_ui()

    def _update_afk_status_ui(self):
        try:
            if self._antiafk_running:
                self._afk_status_lbl.config(text="● Running", fg=ACCENT)
            else:
                self._afk_status_lbl.config(text="○ Stopped", fg=TEXT_FAINT)
        except Exception:
            pass

    def _start_antiafk(self):
        if not WIN32_AVAILABLE:
            self._toast("⚠  pywin32 not installed — pip install pywin32 psutil")
            return
        self._antiafk_stop_event.clear()
        self._antiafk_running = True
        self._antiafk_thread = threading.Thread(
            target=self._antiafk_loop, daemon=True)
        self._antiafk_thread.start()
        if self._antiafk_user_safe.get():
            self._start_activity_monitor()
        self._log_activity("▶ Anti-AFK started")
        self._toast("▶  Anti-AFK started")

    def _stop_antiafk(self):
        self._antiafk_stop_event.set()
        self._antiafk_running = False
        self._stop_activity_monitor()
        self._log_activity("■ Anti-AFK stopped")
        self._toast("■  Anti-AFK stopped")

    def _afk_find_roblox_windows(self, include_hidden=True):
        if not WIN32_AVAILABLE:
            return []
        windows = []
        def _cb(hwnd, _):
            try:
                if include_hidden or win32gui.IsWindowVisible(hwnd):
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    proc = psutil.Process(pid)
                    if proc.name().lower() == "robloxplayerbeta.exe":
                        title = win32gui.GetWindowText(hwnd)
                        if title and "Roblox" in title and not any(
                                x in title for x in ["MSCTFIME", "Default IME", "NVIDIA"]):
                            windows.append(hwnd)
            except (psutil.NoSuchProcess, psutil.AccessDenied, Exception):
                pass
            return True
        win32gui.EnumWindows(_cb, None)
        return windows

    def _afk_show_windows(self):
        windows = self._afk_find_roblox_windows(include_hidden=True)
        shown = 0
        for hwnd in windows:
            if not win32gui.IsWindowVisible(hwnd) or win32gui.IsIconic(hwnd):
                if win32gui.IsIconic(hwnd):
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
                win32gui.SetForegroundWindow(hwnd)
                shown += 1
        self._toast(f"□  Showed {shown} Roblox window(s)")
        self._log_activity(f"□ Showed {shown} Roblox window(s)")

    def _afk_hide_windows(self):
        windows = self._afk_find_roblox_windows(include_hidden=False)
        for hwnd in windows:
            win32gui.ShowWindow(hwnd, win32con.SW_HIDE)
        self._toast(f"■  Hid {len(windows)} Roblox window(s)")
        self._log_activity(f"■ Hid {len(windows)} Roblox window(s)")

    def _afk_refresh_window_list(self, frame):
        """Rebuild the live window inspector in the Anti-AFK tab."""
        for w in frame.winfo_children():
            w.destroy()
        windows = self._afk_find_roblox_windows(include_hidden=True)
        if not windows:
            lbl(frame, "No Roblox windows found", fg=TEXT_FAINT, bg=BG_CARD,
                font=("Segoe UI", 8), pady=4).pack(anchor="w")
            return
        for hwnd in windows:
            try:
                title = win32gui.GetWindowText(hwnd)
                rect  = win32gui.GetClientRect(hwnd)
                w_px  = rect[2] - rect[0]
                h_px  = rect[3] - rect[1]
                vis   = win32gui.IsWindowVisible(hwnd)
                row = fr(frame, bg=BG_ITEM)
                row.config(highlightthickness=1, highlightbackground=BORDER_ITEM)
                row.pack(fill="x", pady=2)
                dot_cv = tk.Canvas(row, width=8, height=8, bg=BG_ITEM,
                                   highlightthickness=0)
                dot_cv.create_oval(1, 1, 7, 7,
                                   fill=ACCENT if vis else TEXT_FAINT, outline="")
                dot_cv.pack(side="left", padx=(6, 4), pady=6)
                lbl(row, f"HWND {hwnd}", fg=ACCENT, bg=BG_ITEM,
                    font=("Consolas", 8, "bold")).pack(side="left")
                lbl(row, f"  {title[:40]}",
                    fg=TEXT_MUTED, bg=BG_ITEM, font=("Segoe UI", 8)).pack(side="left")
                lbl(row, f"  {w_px}×{h_px}  {'visible' if vis else 'hidden'}",
                    fg=TEXT_FAINT, bg=BG_ITEM, font=("Segoe UI", 7)).pack(side="left")
                test_b = lbl(row, "▶ Test", fg=ACCENT, bg=BG_ITEM,
                             font=("Segoe UI", 7), cursor="hand2", padx=6)
                test_b.pack(side="right", pady=4)
                test_b.bind("<Button-1>",
                            lambda e, h=hwnd: threading.Thread(
                                target=self._afk_perform_action, args=(h,), daemon=True).start())
                test_b.bind("<Enter>", lambda e, b=test_b: b.config(fg=TEXT_PRIMARY))
                test_b.bind("<Leave>", lambda e, b=test_b: b.config(fg=ACCENT))
            except Exception:
                pass

    def _afk_tick_window_count(self):
        """Update the window count label every 2 s while Anti-AFK tab is open."""
        try:
            if self.active_page == "antiafk":
                windows = self._afk_find_roblox_windows(include_hidden=True)
                self._afk_win_count_lbl.config(
                    text=f"{len(windows)} window(s) found",
                    fg=ACCENT if windows else TEXT_FAINT)
        except Exception:
            pass
        self.root.after(2000, self._afk_tick_window_count)

    def _afk_test_action(self):
        windows = self._afk_find_roblox_windows(include_hidden=True)
        if not windows:
            self._toast("⚠  No Roblox windows found")
            return
        act = self._antiafk_action.get()
        n = len(windows)
        def _run():
            for hwnd in windows:
                self._afk_perform_action(hwnd, act)
        threading.Thread(target=_run, daemon=True).start()
        self._toast(f"▶  Test '{act}' sent to {n} window(s)")

    def _afk_perform_action(self, hwnd, action_type=None):
        """
        Focus the Roblox window, perform the action, then restore the previous
        foreground window.  Roblox requires real focus to register input — it
        filters out background PostMessage events.

        Flow:
          1. Save the current foreground window.
          2. If Roblox is minimised, restore it first (minimised windows can't
             receive input even when focused).
          3. Use AttachThreadInput + SetForegroundWindow to bring Roblox to front.
          4. Send the action using real keybd_event / mouse_event (not PostMessage).
          5. Re-minimise Roblox if it was minimised before.
          6. Restore the previous foreground window.
        """
        if not WIN32_AVAILABLE:
            return False
        if not win32gui.IsWindow(hwnd):
            return False
        title = win32gui.GetWindowText(hwnd)
        if not title or "Roblox" not in title:
            return False

        if action_type is None:
            action_type = self._antiafk_action.get()

        hold_ms = max(20, min(500, self._afk_click_hold_ms.get()))
        hold_s  = hold_ms / 1000.0

        try:
            user32   = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32

            prev_hwnd  = win32gui.GetForegroundWindow()
            was_iconic = win32gui.IsIconic(hwnd)

            if was_iconic:
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                time.sleep(0.15)

            cur_tid  = kernel32.GetCurrentThreadId()
            prev_tid = win32process.GetWindowThreadProcessId(prev_hwnd)[0]
            rbl_tid  = win32process.GetWindowThreadProcessId(hwnd)[0]

            if prev_tid and prev_tid != cur_tid:
                user32.AttachThreadInput(cur_tid, prev_tid, True)
            if rbl_tid and rbl_tid != cur_tid:
                user32.AttachThreadInput(cur_tid, rbl_tid, True)

            win32gui.SetForegroundWindow(hwnd)
            time.sleep(0.10)

            KEYEVENTF_KEYUP  = 0x0002
            MOUSEEVENTF_MOVE         = 0x0001
            MOUSEEVENTF_LEFTDOWN     = 0x0002
            MOUSEEVENTF_LEFTUP       = 0x0004
            MOUSEEVENTF_ABSOLUTE     = 0x8000

            def _key_down(vk):
                sc = user32.MapVirtualKeyW(vk, 0)
                user32.keybd_event(vk, sc, 0, 0)

            def _key_up(vk):
                sc = user32.MapVirtualKeyW(vk, 0)
                user32.keybd_event(vk, sc, KEYEVENTF_KEYUP, 0)

            def _press(vk, duration=hold_s):
                _key_down(vk)
                time.sleep(duration)
                _key_up(vk)

            def _click():
                rect = win32gui.GetClientRect(hwnd)
                cw = rect[2] - rect[0]
                ch = rect[3] - rect[1]
                px = int(cw * self._afk_click_x_pct.get() / 100)
                py = int(ch * self._afk_click_y_pct.get() / 100)
                pt = win32gui.ClientToScreen(hwnd, (px, py))
                user32.SetCursorPos(pt[0], pt[1])
                time.sleep(0.05)
                user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                time.sleep(hold_s)
                user32.mouse_event(MOUSEEVENTF_LEFTUP,   0, 0, 0, 0)

            if action_type == "click":
                _click()
            elif action_type == "click+space":
                _click()
                time.sleep(0.12)
                _press(0x20)
            elif action_type == "space":
                _press(0x20)
            elif action_type == "ws":
                _press(ord("W"))
                time.sleep(0.10)
                _press(ord("S"))
            elif action_type == "zoom":
                _press(ord("I"))
                time.sleep(0.10)
                _press(ord("O"))
            else:
                _click()

            time.sleep(0.08)

            if was_iconic:
                win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
                time.sleep(0.08)

            if prev_hwnd and win32gui.IsWindow(prev_hwnd) and prev_hwnd != hwnd:
                try:
                    win32gui.SetForegroundWindow(prev_hwnd)
                except Exception:
                    pass

            if prev_tid and prev_tid != cur_tid:
                user32.AttachThreadInput(cur_tid, prev_tid, False)
            if rbl_tid and rbl_tid != cur_tid:
                user32.AttachThreadInput(cur_tid, rbl_tid, False)

            return True

        except Exception:
            return False
    def _antiafk_loop(self):
        interval       = self._antiafk_interval.get()
        action_type    = self._antiafk_action.get()
        user_safe      = self._antiafk_user_safe.get()
        seq_delay      = max(1.5, self._antiafk_seq_delay.get())
        MAX_WAIT       = 1140
        last_action    = time.time() - interval + 10
        last_status_t  = 0

        while not self._antiafk_stop_event.is_set():
            try:
                now     = time.time()
                elapsed = now - last_action
                windows = self._afk_find_roblox_windows(include_hidden=True)

                if not windows:
                    if self._antiafk_stop_event.wait(5):
                        break
                    continue

                if user_safe:
                    is_active  = self._antiafk_user_active
                    inactive_t = now - self._antiafk_last_activity
                    do_action  = (not is_active and inactive_t >= 5 and elapsed >= interval) \
                                 or elapsed >= MAX_WAIT
                else:
                    do_action = elapsed >= interval

                if now - last_status_t > 60:
                    self.root.after(0, lambda e=int(elapsed), i=interval:
                        self._log_activity(
                            f"🤖 Anti-AFK: {e}s elapsed / {i}s interval"))
                    last_status_t = now

                if do_action:
                    n = len(windows)
                    self.root.after(0, lambda n2=n: self._log_activity(
                        f"🤖 Anti-AFK click on {n2} window(s)"))

                    for i, hwnd in enumerate(windows):
                        if self._antiafk_stop_event.is_set():
                            break
                        self._afk_perform_action(hwnd, action_type)
                        if i < n - 1:
                            import random
                            stagger = seq_delay + random.uniform(0.0, 1.0)
                            if self._antiafk_stop_event.wait(stagger):
                                break

                    last_action = time.time()
                    self.root.after(0, lambda: self._toast("🤖 Anti-AFK clicked all windows"))

                if self._antiafk_stop_event.wait(1.0):
                    break
            except Exception:
                if self._antiafk_stop_event.wait(5):
                    break

        self._antiafk_running = False
        self.root.after(0, self._update_afk_status_ui)


    def _start_activity_monitor(self):
        if self._antiafk_monitor_thread and self._antiafk_monitor_thread.is_alive():
            return
        self._antiafk_monitor_stop.clear()
        self._antiafk_last_activity = time.time()
        self._antiafk_monitor_thread = threading.Thread(
            target=self._activity_monitor_loop, daemon=True)
        self._antiafk_monitor_thread.start()

    def _stop_activity_monitor(self):
        self._antiafk_monitor_stop.set()

    def _activity_monitor_loop(self):
        if not WIN32_AVAILABLE:
            return
        last_pos        = win32gui.GetCursorPos()
        last_foreground = win32gui.GetForegroundWindow()
        mouse_btns      = [0x01, 0x02, 0x04]
        btn_states      = {b: False for b in mouse_btns}
        INACTIVITY_WAIT = 5

        while not self._antiafk_monitor_stop.is_set():
            activity = False
            for vk in [0x08, 0x09, 0x0D, 0x10, 0x11, 0x12, 0x20,
                       0x25, 0x26, 0x27, 0x28,
                       *range(65, 91), *range(48, 58)]:
                if ctypes.windll.user32.GetAsyncKeyState(vk) & 0x8000:
                    activity = True
                    break
            if not activity:
                for btn in mouse_btns:
                    state = bool(ctypes.windll.user32.GetKeyState(btn) & 0x8000)
                    if state or (btn_states[btn] and not state):
                        activity = True
                    btn_states[btn] = state
            if not activity:
                cur_pos = win32gui.GetCursorPos()
                if cur_pos != last_pos:
                    activity = True
                last_pos = cur_pos
            if not activity:
                try:
                    cur_fg = win32gui.GetForegroundWindow()
                    if cur_fg != last_foreground:
                        activity = True
                    last_foreground = cur_fg
                except Exception:
                    pass

            if activity:
                self._antiafk_last_activity = time.time()
                self._antiafk_user_active   = True
            else:
                if time.time() - self._antiafk_last_activity >= INACTIVITY_WAIT:
                    self._antiafk_user_active = False

            time.sleep(0.02)

    def _page_activity(self, parent):
        page = fr(parent, bg=BG_BASE)
        page.columnconfigure(0, weight=1)
        page.rowconfigure(1, weight=1)

        hdr = fr(page, bg=BG_BASE)
        hdr.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))
        lbl(hdr, "Activity Log", fg=TEXT_PRIMARY, bg=BG_BASE,
            font=("Segoe UI", 14, "bold")).pack(side="left")
        icon_btn(hdr, "Clear", command=self._clear_activity,
                 hover_fg=RED, hover_bg=RED_BG).pack(side="right")

        sf = ScrollFrame(page, bg=BG_BASE)
        sf.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self._activity_sf = sf
        self._refresh_activity_display()
        return page

    def _refresh_activity_display(self):
        if not hasattr(self, "_activity_sf"):
            return
        inn = self._activity_sf.inner
        for w in inn.winfo_children():
            w.destroy()
        inn.columnconfigure(0, weight=1)
        if not self._activity_log:
            lbl(inn, "No activity yet. Start the macro to begin logging.",
                fg=TEXT_FAINT, bg=BG_BASE, font=("Segoe UI", 8),
                pady=20).pack(padx=12)
            return
        for ts, msg in reversed(self._activity_log[-200:]):
            row = fr(inn, bg=BG_ITEM)
            row.config(highlightthickness=1, highlightbackground=BORDER_ITEM)
            row.pack(fill="x", pady=1)
            lbl(row, ts, fg=TEXT_FAINT, bg=BG_ITEM,
                font=("Consolas", 7), padx=6).pack(side="left")
            lbl(row, msg, fg=TEXT_MUTED, bg=BG_ITEM,
                font=("Segoe UI", 8), padx=4).pack(side="left", fill="x", expand=True)

    def _log_activity(self, msg):
        ts = time.strftime("%H:%M:%S")
        self._activity_log.append((ts, msg))
        if len(self._activity_log) > 500:
            self._activity_log = self._activity_log[-500:]
        if self.active_page == "activity":
            self.root.after(0, self._refresh_activity_display)

    def _clear_activity(self):
        self._activity_log.clear()
        self._refresh_activity_display()

    def _page_biome_actions(self, parent):
        page = fr(parent, bg=BG_BASE)
        page.columnconfigure(0, weight=1)
        page.rowconfigure(1, weight=1)

        lbl(page, "Biome Actions", fg=TEXT_PRIMARY, bg=BG_BASE,
            font=("Segoe UI", 14, "bold")).grid(row=0, column=0, sticky="w",
                                                padx=12, pady=(12, 4))
        sf = ScrollFrame(page, bg=BG_BASE)
        sf.grid(row=1, column=0, sticky="nsew")
        inn = sf.inner
        inn.columnconfigure(0, weight=1)

        uid_c = card(inn)
        uid_c.grid(row=0, column=0, sticky="ew", padx=12, pady=(8, 4))
        uh = fr(uid_c, bg=BG_CARD)
        uh.pack(fill="x", padx=12, pady=(10, 2))
        lbl(uh, "DISCORD USER ID", fg=TEXT_FAINT, bg=BG_CARD,
            font=("Segoe UI", 8, "bold")).pack(side="left")
        lbl(uh, "for tagging you in alerts", fg=TEXT_FAINT, bg=BG_CARD,
            font=("Segoe UI", 7)).pack(side="right")
        uid_row = fr(uid_c, bg=BG_CARD)
        uid_row.pack(fill="x", padx=12, pady=(4, 4))
        uid_e = styled_entry(uid_row, textvariable=self.discord_user_id)
        uid_e.pack(fill="x", ipady=5)
        sf.bind_mousewheel(uid_e)
        lbl(uid_c,
            "ℹ  Discord Settings → Advanced → Developer Mode → right-click name → Copy User ID",
            fg=TEXT_FAINT, bg=BG_CARD, font=("Segoe UI", 7),
            wraplength=480, justify="left").pack(anchor="w", padx=12, pady=(0, 8))

        alert_c = card(inn)
        alert_c.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 4))

        ah = fr(alert_c, bg=BG_CARD)
        ah.pack(fill="x", padx=12, pady=(10, 2))
        lbl(ah, "BIOME ALERTS", fg=TEXT_FAINT, bg=BG_CARD,
            font=("Segoe UI", 8, "bold")).pack(side="left")
        lbl(ah, "Dreamspace / Cyberspace / Glitched → always @everyone",
            fg=TEXT_FAINT, bg=BG_CARD, font=("Segoe UI", 7)).pack(side="right")

        col_hdr = fr(alert_c, bg=BG_CARD)
        col_hdr.pack(fill="x", padx=12, pady=(4, 0))
        lbl(col_hdr, "Biome", fg=TEXT_FAINT, bg=BG_CARD,
            font=("Segoe UI", 8)).pack(side="left", padx=(24, 0))
        lbl(col_hdr, "Tag User", fg=ACCENT, bg=BG_CARD,
            font=("Segoe UI", 8)).pack(side="right", padx=(0, 8))
        lbl(col_hdr, "No Tag", fg=TEXT_MUTED, bg=BG_CARD,
            font=("Segoe UI", 8)).pack(side="right", padx=(0, 24))

        sep(alert_c, BORDER).pack(fill="x", padx=12, pady=4)

        for name, color, always_ev, *_ in BIOMES:
            biome_info   = BIOME_DATA.get(name, {})
            force_notify = biome_info.get("force_notify", False)
            never_notify = biome_info.get("never_notify", False)
            emoji        = biome_info.get("emoji", "")
            row = fr(alert_c, bg=BG_CARD)
            row.pack(fill="x", padx=10, pady=1)
            dot(row, color, BG_CARD).pack(side="left", padx=(4, 6), pady=5)
            lbl(row, f"{emoji} {name}" if emoji else name, fg=TEXT_MUTED, bg=BG_CARD,
                font=("Segoe UI", 9)).pack(side="left", fill="x", expand=True)
            sf.bind_mousewheel(row)

            if force_notify:
                tag_lbl = "Always @everyone" if biome_info.get("ping_everyone") else "Always notify"
                lbl(row, tag_lbl, fg=color, bg=BG_CARD,
                    font=("Segoe UI", 8, "bold"), padx=8).pack(side="right")
            elif never_notify:
                lbl(row, "Never notify", fg=TEXT_FAINT, bg=BG_CARD,
                    font=("Segoe UI", 8), padx=8).pack(side="right")
            else:
                if name not in self.biome_alert_vars:
                    is_rare = biome_info.get("force_notify", False)
                    fallback = "Tag" if is_rare else "No Tag"
                    default = self._pending_biome_alerts.get(name, fallback)
                    self.biome_alert_vars[name] = tk.StringVar(value=default)
                var = self.biome_alert_vars[name]
                for mode in ["Tag", "No Tag"]:
                    rb = tk.Radiobutton(
                        row, text="", variable=var, value=mode,
                        bg=BG_CARD, fg=ACCENT if mode == "Tag" else TEXT_MUTED,
                        selectcolor=BG_ITEM, activebackground=BG_CARD,
                        highlightthickness=0, bd=0, cursor="hand2",
                        command=lambda n=name, v=var: self._toast(
                            f"{'🔔' if v.get()=='Tag' else '🔕'}  {n} → {v.get()}")
                    )
                    rb.pack(side="right", padx=12)
                    sf.bind_mousewheel(rb)

        tk.Frame(alert_c, bg=BG_CARD, height=8).pack()

        aura_c = card(inn)
        aura_c.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 4))

        ah2 = fr(aura_c, bg=BG_CARD)
        ah2.pack(fill="x", padx=12, pady=(10, 2))
        lbl(ah2, "AURA DETECTION", fg=TEXT_FAINT, bg=BG_CARD,
            font=("Segoe UI", 8, "bold")).pack(side="left")
        lbl(ah2, f"{len(AURA_DATA)} auras tracked", fg=TEXT_FAINT, bg=BG_CARD,
            font=("Segoe UI", 7)).pack(side="right")

        lbl(aura_c,
            "✨  Aura equips are detected automatically from Roblox logs and sent to your webhooks.\n"
            "    Webhooks will always tag you (uses your Discord User ID above). "
            "No extra configuration needed.",
            fg=TEXT_MUTED, bg=BG_CARD, font=("Segoe UI", 8),
            wraplength=480, justify="left").pack(anchor="w", padx=12, pady=(4, 2))

        sep(aura_c, BORDER).pack(fill="x", padx=12, pady=4)

        preview_frame = fr(aura_c, bg=BG_CARD)
        preview_frame.pack(fill="x", padx=12, pady=(0, 4))
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.columnconfigure(1, weight=1)

        col_hdr2 = fr(aura_c, bg=BG_CARD)
        col_hdr2.pack(fill="x", padx=12, pady=(0, 2))
        lbl(col_hdr2, "Aura Name", fg=TEXT_FAINT, bg=BG_CARD,
            font=("Segoe UI", 8)).pack(side="left", padx=(4, 0))
        lbl(col_hdr2, "Odds", fg=TEXT_FAINT, bg=BG_CARD,
            font=("Segoe UI", 8)).pack(side="right", padx=(0, 4))

        for aura_name, odds in AURA_DATA[-10:]:
            arow = fr(aura_c, bg=BG_CARD)
            arow.pack(fill="x", padx=10, pady=1)
            lbl(arow, f"✨ {aura_name}", fg=TEXT_MUTED, bg=BG_CARD,
                font=("Segoe UI", 8)).pack(side="left", padx=(4, 0))
            lbl(arow, odds, fg=PURPLE, bg=BG_CARD,
                font=("Segoe UI", 8)).pack(side="right", padx=(0, 8))
            sf.bind_mousewheel(arow)

        lbl(aura_c, f"  … and {len(AURA_DATA) - 10} more auras",
            fg=TEXT_FAINT, bg=BG_CARD, font=("Segoe UI", 7)).pack(
                anchor="w", padx=12, pady=(0, 8))

        accent_btn(inn, "💾  Save Alert Settings",
                   command=self._save_alerts, padx=14, pady=6).grid(
            row=3, column=0, padx=12, pady=10, sticky="w")
        return page

    def _page_launch(self, parent):
        page = fr(parent, bg=BG_BASE)
        page.columnconfigure(0, weight=1)
        page.rowconfigure(1, weight=1)

        lbl(page, "Launch", fg=TEXT_PRIMARY, bg=BG_BASE,
            font=("Segoe UI", 14, "bold")).grid(row=0, column=0, sticky="w",
                                                padx=12, pady=(12, 6))
        sf = ScrollFrame(page, bg=BG_BASE)
        sf.grid(row=1, column=0, sticky="nsew")
        inn = sf.inner
        inn.columnconfigure(0, weight=1)

        cnt_c = card(inn)
        cnt_c.grid(row=0, column=0, sticky="ew", padx=12, pady=(8, 4))
        lbl(cnt_c, "INSTANCES TO OPEN", fg=TEXT_FAINT, bg=BG_CARD,
            font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=12, pady=(10, 4))

        cr = fr(cnt_c, bg=BG_CARD)
        cr.pack(padx=12, anchor="w", pady=(0, 4))
        self._instance_count = tk.IntVar(value=2)
        cv = lbl(cr, "2", fg=ACCENT, bg=BG_CARD, font=("Consolas", 22, "bold"))
        cv.pack(side="left", padx=(0, 12))

        def _dec():
            v = self._instance_count.get()
            if v > 1:
                self._instance_count.set(v - 1)
                cv.config(text=str(v - 1))

        def _inc():
            v = self._instance_count.get()
            if v < 12:
                self._instance_count.set(v + 1)
                cv.config(text=str(v + 1))

        btn_col = fr(cr, bg=BG_CARD)
        btn_col.pack(side="left")
        icon_btn(btn_col, " + ", fg=TEXT_MUTED, bg=BG_ITEM,
                  font=("Segoe UI", 12, "bold"),
                  command=_inc, padx=8, pady=2).pack(side="top", pady=1)
        icon_btn(btn_col, " − ", fg=TEXT_MUTED, bg=BG_ITEM,
                  font=("Segoe UI", 12, "bold"),
                  command=_dec, padx=8, pady=2).pack(side="top", pady=1)

        lbl(cr, "instances  (1–12)", fg=TEXT_FAINT, bg=BG_CARD,
            font=("Segoe UI", 8)).pack(side="left", padx=(10, 0))

        delay_r = fr(cnt_c, bg=BG_CARD)
        delay_r.pack(fill="x", padx=12, pady=(4, 4))
        lbl(delay_r, "Launch delay between instances (seconds)",
            fg=TEXT_FAINT, bg=BG_CARD, font=("Segoe UI", 8)).pack(anchor="w")
        self._delay_entry = styled_entry(delay_r, width=6)
        self._delay_entry.insert(0, "3")
        self._delay_entry.pack(side="left", ipady=5, pady=(2, 0))
        lbl(delay_r, "  seconds", fg=TEXT_FAINT, bg=BG_CARD,
            font=("Segoe UI", 8)).pack(side="left")

        mx_c = card(inn)
        mx_c.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 4))
        lbl(mx_c, "MULTI-INSTANCE (MUTEX)", fg=TEXT_FAINT, bg=BG_CARD,
            font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=12, pady=(10, 2))
        lbl(mx_c,
            "MultiFInstance holds the ROBLOX_singletonEvent mutex before each launch so "
            "Roblox cannot close the previous instance. Mutex handles are kept alive for the "
            "entire session. On Windows only.",
            fg=TEXT_DIM, bg=BG_CARD, font=("Segoe UI", 8),
            wraplength=520, justify="left").pack(anchor="w", padx=12, pady=(0, 10))

        self._mutex_status = lbl(mx_c, f"Mutexes held: {len(self._roblox_mutexes)}",
                                 fg=ACCENT, bg=BG_CARD, font=("Segoe UI", 8))
        self._mutex_status.pack(anchor="w", padx=12, pady=(0, 10))

        accent_btn(inn, "▶  Launch Instances",
                   command=self._do_launch, padx=18, pady=8).grid(
            row=2, column=0, padx=12, pady=8, sticky="w")

        red_btn(inn, "✕  Release All Mutexes",
                command=self._release_mutexes, padx=14, pady=6).grid(
            row=3, column=0, padx=12, pady=(0, 4), sticky="w")

        info_c = card(inn)
        info_c.grid(row=4, column=0, sticky="ew", padx=12, pady=(0, 12))
        lbl(info_c,
            "ℹ  After launching, go to the Instances tab to configure each instance's "
            "username, private server link, and webhook URL.",
            fg=TEXT_FAINT, bg=BG_CARD, font=("Segoe UI", 8),
            wraplength=520, justify="left").pack(anchor="w", padx=12, pady=10)

        return page


    def _on_start(self):
        if self.running:
            return
        self.running = True
        self.macro_start = time.time()
        if self._detection_mgr:
            self._detection_mgr.account_biomes      = {}
            self._detection_mgr.account_auras       = {}
            self._detection_mgr.account_aura_offsets = {}
            self._detection_mgr.sent_webhooks_cache = set()
            self._detection_mgr.log_start_offsets   = {}
            self._detection_mgr.app_start_time      = time.time()
            self._detection_mgr._update_log_map()
        self._update_status_ui()
        self._log_activity("▶ Macro started")
        self._toast("▶  Macro started")
        self._send_macro_status_webhooks("started")

    def _on_stop(self):
        if not self.running:
            return
        self.running = False
        self.macro_start = None
        self._update_status_ui()
        self._log_activity("■ Macro stopped")
        self._toast("■  Macro stopped")
        self._send_macro_status_webhooks("stopped")

    def _toggle_macro(self):
        if self.running:
            self._on_stop()
        else:
            self._on_start()

    def _update_status_ui(self):
        try:
            if self.running:
                self._status_lbl.config(text="Active", fg=ACCENT)
                self._status_sub.config(text="Monitoring biomes…")
                self._pulse_cv.itemconfig("dot", fill=ACCENT)
                self._play_cv.delete("icon")
                self._play_cv.create_rectangle(9, 8, 14, 23, fill="#061510", tags="icon")
                self._play_cv.create_rectangle(18, 8, 23, 23, fill="#061510", tags="icon")
                self._play_cv.itemconfig("bg", fill=ACCENT)
                self._play_cv.bind("<Enter>",
                    lambda e=None: self._play_cv.itemconfig("bg", fill=ACCENT_HOVER))
                self._play_cv.bind("<Leave>",
                    lambda e=None: self._play_cv.itemconfig("bg", fill=ACCENT))
                try:
                    self._topbar_status_lbl.config(text="● Running", fg=ACCENT)
                    self._topbar_status_dot.itemconfig("d", fill=ACCENT)
                    self._topbar_status_pill.config(bg=ACCENT_DIM,
                                                    highlightbackground=ACCENT)
                    self._topbar_status_dot.config(bg=ACCENT_DIM)
                    self._topbar_status_lbl.config(bg=ACCENT_DIM)
                except Exception: pass
            else:
                self._status_lbl.config(text="Stopped", fg=TEXT_DIM)
                self._status_sub.config(text="Press F8 to start")
                self._pulse_cv.itemconfig("dot", fill=RED)
                self._play_cv.delete("icon")
                self._play_cv.create_polygon(11, 8, 23, 16, 11, 24,
                                             fill="#ffffff", tags="icon")
                self._play_cv.itemconfig("bg", fill=RED)
                self._play_cv.bind("<Enter>",
                    lambda e=None: self._play_cv.itemconfig("bg", fill=RED_HOVER))
                self._play_cv.bind("<Leave>",
                    lambda e=None: self._play_cv.itemconfig("bg", fill=RED))
                try:
                    self._timer_lbl.config(text="00:00:00")
                except Exception:
                    pass
                try:
                    self._topbar_status_lbl.config(text="● Stopped", fg=RED, bg=RED_BG)
                    self._topbar_status_dot.itemconfig("d", fill=RED)
                    self._topbar_status_dot.config(bg=RED_BG)
                    self._topbar_status_pill.config(bg=RED_BG,
                                                    highlightbackground="#3a1520")
                except Exception: pass
            try:
                self._sb_dot_cv.itemconfig("dot",
                    fill=ACCENT if self.running else TEXT_FAINT)
            except Exception:
                pass
        except Exception:
            pass


    def _tick_timer(self):
        try:
            if self.running and self.macro_start:
                e = int(time.time() - self.macro_start)
                if self._dash_alive:
                    self._timer_lbl.config(
                        text=f"{e//3600:02d}:{(e%3600)//60:02d}:{e%60:02d}")
        except Exception:
            pass
        self.root.after(1000, self._tick_timer)

    def _tick_auto_scan(self):
        self._silent_scan()
        self.root.after(10_000, self._tick_auto_scan)

    def _tick_log_watcher(self):
        if self._detection_mgr:
            if not getattr(self, "_detection_running", False):
                self._detection_running = True
                def _run():
                    try:
                        self._detection_mgr._update_log_map()
                        self._detection_mgr.check_all_accounts()
                    finally:
                        self._detection_running = False
                threading.Thread(target=_run, daemon=True).start()
        try: self._refresh_instance_chips()
        except Exception: pass
        if self.active_page == "dashboard":
            try: self._refresh_log_frame()
            except Exception: pass
        if self.active_page == "webhooks":
            try: self._wh_refresh_chips()
            except Exception: pass
        self.root.after(2_000, self._tick_log_watcher)

    def _tick_autosave(self):
        self._save_config()
        self.root.after(60_000, self._tick_autosave)


    def _setup_roblox_feature_flags(self):
        """Apply FastFlags for trace logging — covers Bloxstrap, Fishstrap, and vanilla Roblox."""
        if sys.platform != "win32":
            return
        flags = {
            "FStringDebugLuaLogLevel":   "trace",
            "FStringDebugLuaLogPattern": "ExpChat/mountClientApp",
        }
        local     = os.environ.get("LOCALAPPDATA", "")
        written   = 0
        updated   = 0

        def _write_flags(json_path, label):
            nonlocal written, updated
            try:
                os.makedirs(os.path.dirname(json_path), exist_ok=True)
                existing  = {}
                file_existed = os.path.exists(json_path)
                if file_existed:
                    try:
                        with open(json_path, "r", encoding="utf-8") as f:
                            content = f.read()
                            if content.strip():
                                existing = json.loads(content)
                    except Exception:
                        existing = {}
                needs = any(existing.get(k) != v for k, v in flags.items())
                if needs:
                    existing.update(flags)
                    with open(json_path, "w", encoding="utf-8") as f:
                        json.dump(existing, f, indent=2)
                    if file_existed:
                        updated += 1
                    else:
                        written += 1
            except Exception:
                pass

        for launcher in ("Bloxstrap", "Fishstrap"):
            launcher_dir = os.path.join(local, launcher)
            if os.path.isdir(launcher_dir):
                _write_flags(
                    os.path.join(launcher_dir, "Modifications", "ClientSettings",
                                 "ClientAppSettings.json"),
                    launcher
                )

        versions_dir = os.path.join(local, "Roblox", "Versions")
        if os.path.isdir(versions_dir):
            try:
                for ver in os.listdir(versions_dir):
                    ver_path = os.path.join(versions_dir, ver)
                    if os.path.isdir(ver_path) and ver.startswith("version-"):
                        _write_flags(
                            os.path.join(ver_path, "ClientSettings",
                                         "ClientAppSettings.json"),
                            f"Roblox/{ver}"
                        )
            except OSError:
                pass

        total = written + updated
        if total:
            self.root.after(0, lambda: self._log_activity(
                f"⚙ FastFlags applied: {written} new, {updated} updated location(s)"))
        else:
            self.root.after(0, lambda: self._log_activity(
                "⚙ FastFlags already up to date"))


    def _on_account_biome_change(self, username, biome_name, private_server,
                                  ping_everyone=False, force_notify=False):
        """Called by DetectionManager on main thread when a biome changes for an account."""
        self.biome_counts[biome_name] = self.biome_counts.get(biome_name, 0) + 1
        try:
            lw = self._biome_count_labels.get(biome_name)
            if lw:
                lw.config(text=str(self.biome_counts[biome_name]), fg=ACCENT)
        except Exception:
            pass

        biome_info    = BIOME_DATA.get(biome_name, {})
        never_notify  = biome_info.get("never_notify", False)
        if never_notify and not force_notify:
            return

        emoji      = biome_info.get("emoji", "🌍")
        color_hex  = biome_info.get("color", "0x00e5a0").replace("0x", "#")
        try:
            color_hex = f"#{int(biome_info.get('color', '0x00e5a0').replace('0x', ''), 16):06X}"
        except Exception:
            color_hex = ACCENT

        uname_label = f" ({username})" if username else ""
        self._log_activity(f"{emoji} Biome detected: {biome_name}{uname_label}")
        self._toast(f"{emoji}  {biome_name} detected!{uname_label}")

        src_uname = username.lower() if username else ""

        for wh in self.webhooks:
            url = wh.get("url", "").strip()
            if not url:
                continue
            wh_targets = [t.lower() for t in wh.get("targets", ["all"])]
            if "all" in wh_targets or (src_uname and src_uname in wh_targets):
                self.send_biome_alert(biome_name, color_hex, {
                    "id":              username or "unknown",
                    "roblox_username": username or "",
                    "private_server":  private_server or "",
                    "discord_webhook": url,
                    "ping_everyone":   ping_everyone or biome_info.get("ping_everyone", False),
                    "force_notify":    force_notify,
                })

        for acct in self.accounts:
            if acct.get("roblox_username", "").lower() != src_uname:
                continue
            acct_wh = acct.get("discord_webhook", "").strip()
            if acct_wh and not any(wh.get("url","").strip() == acct_wh for wh in self.webhooks):
                self.send_biome_alert(biome_name, color_hex, {
                    "id":              username or "unknown",
                    "roblox_username": username or "",
                    "private_server":  acct.get("private_server", ""),
                    "discord_webhook": acct_wh,
                    "ping_everyone":   ping_everyone or biome_info.get("ping_everyone", False),
                    "force_notify":    force_notify,
                })
            break


    def _on_biome_detected(self, biome_name, source_inst=None):
        """Legacy shim — new code goes through _on_account_biome_change."""
        uname = source_inst.get("roblox_username", "") if source_inst else ""
        ps    = source_inst.get("private_server", "") if source_inst else ""
        self._on_account_biome_change(uname, biome_name, ps)

    def _on_account_aura_detected(self, username, aura_name, odds, private_server):
        """Called on main thread when a new aura equip is detected."""
        uname_label = f" ({username})" if username else ""
        self._log_activity(f"✨ Aura detected: {aura_name} ({odds}){uname_label}")
        self._toast(f"✨  {aura_name} equipped!{uname_label}")

        src_uname = username.lower() if username else ""
        sent_urls = set()

        for wh in self.webhooks:
            url = wh.get("url", "").strip()
            if not url:
                continue
            wh_targets = [t.lower() for t in wh.get("targets", ["all"])]
            if "all" in wh_targets or (src_uname and src_uname in wh_targets):
                self.send_aura_alert(aura_name, odds, {
                    "roblox_username": username or "",
                    "private_server":  private_server or "",
                    "discord_webhook": url,
                })
                sent_urls.add(url)

        for acct in self.accounts:
            if acct.get("roblox_username", "").lower() != src_uname:
                continue
            acct_wh = acct.get("discord_webhook", "").strip()
            if acct_wh and acct_wh not in sent_urls:
                self.send_aura_alert(aura_name, odds, {
                    "roblox_username": username or "",
                    "private_server":  acct.get("private_server", ""),
                    "discord_webhook": acct_wh,
                })
            break

    def send_aura_alert(self, aura_name, odds, inst):
        """Send a Discord webhook embed for an aura detection."""
        wh = inst.get("discord_webhook", "").strip()
        if not wh:
            return

        uname    = inst.get("roblox_username", "unknown")
        unix_ts  = int(time.time())
        uid      = self.discord_user_id.get().strip()
        ping     = f"<@{uid}>\n" if uid else ""

        desc = [
            f"**Account:** `{uname}`",
            f"**Aura:** ✨ {aura_name}",
            f"**Odds:** `{odds}`",
            f"**Time:** <t:{unix_ts}:F> (<t:{unix_ts}:R>)",
        ]

        embed = {
            "title":       f"✨  Aura Detected — {aura_name}",
            "description": "\n".join(desc),
            "color":       0xf0c040,
            "footer":      {"text": f"MultiFInstance v{VERSION}"},
            "timestamp":   time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

        payload = {"embeds": [embed]}
        if ping:
            payload["content"] = ping

        threading.Thread(target=self._post_webhook, args=(wh, payload), daemon=True).start()


    def _silent_scan(self):
        try:
            found = self._get_roblox_process_count()
            changed = False
            for i, inst in enumerate(self.instances):
                was = inst.get("active", False)
                now = (i < found)
                if was != now:
                    inst["active"] = now
                    changed = True
            if changed:
                try: self._refresh_log_frame()
                except Exception: pass
                try: self._refresh_instance_chips()
                except Exception: pass
        except Exception:
            pass

    def _scan_instances(self):
        found = self._get_roblox_process_count()
        for i, inst in enumerate(self.instances):
            inst["active"] = (i < found)
        while len(self.instances) < found:
            new_id = max((i["id"] for i in self.instances), default=0) + 1
            self.instances.append({
                "id": new_id,
                "roblox_username": "",
                "private_server":  "",
                "discord_webhook": "",
                "active": True,
            })
        try: self._refresh_instance_list()
        except Exception: pass
        try: self._refresh_log_frame()
        except Exception: pass
        try: self._refresh_instance_chips()
        except Exception: pass
        msg = f"⟳  Found {found} Roblox instance(s)" if found else "⟳  No Roblox instances found"
        self._toast(msg)
        self._log_activity(f"⟳ Scan: {found} Roblox instance(s) found")

    def _get_roblox_process_count(self):
        try:
            if sys.platform == "win32":
                result = subprocess.run(
                    ["tasklist", "/FI", "IMAGENAME eq RobloxPlayerBeta.exe",
                     "/FO", "CSV", "/NH"],
                    capture_output=True, text=True, timeout=5,
                    creationflags=0x08000000)
                return len([l for l in result.stdout.splitlines()
                             if "RobloxPlayerBeta" in l])
            else:
                result = subprocess.run(
                    ["pgrep", "-c", "RobloxPlayer"],
                    capture_output=True, text=True, timeout=5)
                return int(result.stdout.strip()) if result.stdout.strip().isdigit() else 0
        except Exception:
            return 0


    def _find_roblox_exe(self):
        """Find RobloxPlayerBeta.exe from all known install locations."""
        local = os.environ.get("LOCALAPPDATA", "")
        candidates = []
        ver_dir = os.path.join(local, "Roblox", "Versions")
        if os.path.isdir(ver_dir):
            for ver in os.listdir(ver_dir):
                p = os.path.join(ver_dir, ver, "RobloxPlayerBeta.exe")
                if os.path.isfile(p):
                    candidates.append(p)
        pkg_dir = os.path.join(local, "Packages")
        if os.path.isdir(pkg_dir):
            try:
                for pkg in os.listdir(pkg_dir):
                    if "ROBLOX" in pkg.upper():
                        for root_w, _, files in os.walk(os.path.join(pkg_dir, pkg)):
                            for fname in files:
                                if fname.lower() == "robloxplayerbeta.exe":
                                    candidates.append(os.path.join(root_w, fname))
            except OSError:
                pass
        for pf in [os.environ.get("PROGRAMFILES", ""), os.environ.get("PROGRAMFILES(X86)", "")]:
            if not pf:
                continue
            vd = os.path.join(pf, "Roblox", "Versions")
            if os.path.isdir(vd):
                for ver in os.listdir(vd):
                    p = os.path.join(vd, ver, "RobloxPlayerBeta.exe")
                    if os.path.isfile(p):
                        candidates.append(p)
        if not candidates:
            return None
        return max(candidates, key=os.path.getmtime)

    def _hold_singleton_mutex(self):
        """
        Create (or open) ROBLOX_singletonEvent and keep the handle alive in
        self._roblox_mutexes.  While we own this handle Roblox cannot close a
        previous instance when a new one starts — each new Roblox process finds
        the mutex already taken and simply joins the session instead of killing it.

        Call this right before launching each Chrome/Roblox instance.
        Returns the raw handle (int) or 0 on failure.
        """
        if sys.platform != "win32":
            return 0
        try:
            import ctypes
            k32 = ctypes.WinDLL("kernel32", use_last_error=True)
            h = k32.CreateMutexW(None, True, "ROBLOX_singletonEvent")
            if h:
                self._roblox_mutexes.append(h)
                return h
        except Exception:
            pass
        return 0

    def _kill_singleton_mutex(self):
        """
        Release + close every handle in _roblox_mutexes and drain any
        remaining OS-level handles so the mutex is fully destroyed.
        Safe to call at shutdown or before a clean restart.
        """
        if sys.platform != "win32":
            return 0
        try:
            import ctypes
            k32 = ctypes.WinDLL("kernel32", use_last_error=True)
            MUTEX_ALL_ACCESS = 0x1F0001
            killed = 0

            for h in list(self._roblox_mutexes):
                try:
                    k32.ReleaseMutex(h)
                    k32.CloseHandle(h)
                    killed += 1
                except Exception:
                    pass
            self._roblox_mutexes.clear()

            for _ in range(32):
                h = k32.OpenMutexW(MUTEX_ALL_ACCESS, False, "ROBLOX_singletonEvent")
                if not h:
                    break
                k32.ReleaseMutex(h)
                k32.CloseHandle(h)
                killed += 1
            return killed
        except Exception:
            return 0

    def _do_launch(self):
        count = self._instance_count.get()
        try:
            delay = float(self._delay_entry.get().strip() or "3")
        except ValueError:
            delay = 3.0

        new_instances = []
        for i in range(1, count + 1):
            existing = next((x for x in self.instances if x["id"] == i), None)
            if existing:
                existing["active"] = True
                new_instances.append(existing)
            else:
                new_instances.append({
                    "id": i,
                    "roblox_username": "",
                    "private_server":  "",
                    "discord_webhook": "",
                    "active": True,
                })
        self.instances = new_instances
        self._log_activity(f"▶ Launching {count} instance(s) — {delay}s delay")
        self._toast(f"▶  Launching {count} instance(s)…")

        def _launch():
            if sys.platform != "win32":
                self.root.after(0, lambda: self._toast("⚠  Launch requires Windows"))
                return

            roblox_exe = self._find_roblox_exe()
            if not roblox_exe:
                self.root.after(0, lambda: self._toast(
                    "⚠  RobloxPlayerBeta.exe not found — is Roblox installed?"))
                self.root.after(0, lambda: self._log_activity(
                    "⚠ Launch failed: RobloxPlayerBeta.exe not found"))
                return

            import ctypes
            shell32 = ctypes.windll.shell32

            for idx, inst in enumerate(self.instances):
                held = self._hold_singleton_mutex()
                self.root.after(0, lambda k=held, n=idx+1: self._log_activity(
                    f"🔒 Mutex held (handle={k}) for instance {n}"))

                time.sleep(0.15)

                ps = inst.get("private_server", "").strip()

                def _to_roblox_uri(link):
                    """
                    Convert any Roblox share URL to a roblox:// deep-link so we
                    never hit the web redirect (which rate-limits after ~2 hits).

                    Handles:
                      https://www.roblox.com/share?code=XXX&type=Server
                      https://www.roblox.com/games/PLACEID/...?privateServerLinkCode=XXX
                    Returns original string unchanged if already roblox:// or unrecognised.
                    """
                    import urllib.parse as _up
                    if not link or link.startswith("roblox://"):
                        return link
                    try:
                        parsed = _up.urlparse(link)
                        qs = _up.parse_qs(parsed.query)
                        if "code" in qs and qs.get("type", [""])[0] == "Server":
                            code = qs["code"][0]
                            return f"roblox://experiences/start?privateServerLinkCode={code}"
                        if "privateServerLinkCode" in qs:
                            code = qs["privateServerLinkCode"][0]
                            parts = [p for p in parsed.path.split("/") if p]
                            place_id = parts[1] if len(parts) >= 2 and parts[0] == "games" else ""
                            if place_id:
                                return f"roblox://experiences/start?placeId={place_id}&privateServerLinkCode={code}"
                            return f"roblox://experiences/start?privateServerLinkCode={code}"
                    except Exception:
                        pass
                    return link

                try:
                    if ps:
                        uri = _to_roblox_uri(ps)
                        shell32.ShellExecuteW(None, "open", uri, None, None, 1)
                    else:
                        DETACHED      = 0x00000008
                        NEW_GRP       = 0x00000200
                        NO_WIN        = 0x08000000
                        subprocess.Popen(
                            [roblox_exe],
                            creationflags=DETACHED | NEW_GRP | NO_WIN,
                            close_fds=True,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                        )
                except Exception as e:
                    err = str(e)
                    self.root.after(0, lambda er=err, n=idx+1: (
                        self._toast(f"⚠  Instance {n} failed: {er[:50]}"),
                        self._log_activity(f"⚠ Instance {n} error: {er}")
                    ))
                    continue

                uname = inst.get("roblox_username") or f"#{inst['id']}"
                self.root.after(0, lambda u=uname, n=idx + 1: (
                    self._log_activity(f"▶ Launched instance {n} ({u})"),
                    self._toast(f"▶  Launched instance {n}…"),
                ))

                if idx < len(self.instances) - 1:
                    time.sleep(delay)

            self.root.after(0, lambda: self._toast(f"✓  All {count} instances launched"))
            self.root.after(0, self._update_mutex_status)

        threading.Thread(target=_launch, daemon=True).start()

    def _release_mutexes(self):
        """Release all held mutex handles and drain any OS-level leftovers."""
        killed = self._kill_singleton_mutex()
        self._update_mutex_status()
        self._toast(f"✕  Mutexes released ({killed} handle(s))")
        self._log_activity(f"✕ Mutexes released ({killed} handle(s))")

    def _update_mutex_status(self):
        try:
            self._mutex_status.config(
                text=f"Mutexes held: {len(self._roblox_mutexes)}")
        except Exception:
            pass


    def _send_test_webhook(self):
        if not self.webhooks:
            self._toast("⚠  No webhooks configured — go to Webhooks tab")
            return
        for wh in self.webhooks:
            url = wh.get("url", "").strip()
            if not url:
                continue
            payload = {"embeds": [{
                "title": "⚡ Test Alert — MultiFInstance",
                "description": f"Webhook **{wh['name']}** is connected.",
                "color": 0x00e5a0,
                "footer": {"text": f"MultiFInstance v{VERSION}"},
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }]}
            threading.Thread(target=self._post_webhook, args=(url, payload), daemon=True).start()
        self._toast("⚡  Sending test to all webhooks…")

    def send_biome_alert(self, biome_name, color_hex, inst):
        wh = inst.get("discord_webhook", "").strip()
        if not wh:
            return

        biome_info    = BIOME_DATA.get(biome_name, {})
        force_notify  = inst.get("force_notify", False) or biome_info.get("force_notify", False)
        ping_everyone = inst.get("ping_everyone", False) or biome_info.get("ping_everyone", False)
        never_notify  = biome_info.get("never_notify", False)
        if never_notify and not force_notify:
            return


        alert_var  = self.biome_alert_vars.get(biome_name)
        do_tag     = alert_var and alert_var.get() == "Tag"
        uid        = self.discord_user_id.get().strip()

        if ping_everyone or (force_notify and biome_info.get("ping_everyone", False)):
            ping = "@everyone\n"
        elif do_tag and uid:
            ping = f"<@{uid}>\n"
        else:
            ping = ""

        try:
            color_int = int(color_hex.lstrip("#"), 16)
        except Exception:
            color_int = 0x00e5a0

        emoji      = biome_info.get("emoji", "🌍")
        uname      = inst.get("roblox_username") or f"Instance #{inst.get('id', '?')}"
        ps_link    = inst.get("private_server", "").strip()
        unix_ts    = int(time.time())
        thumb_url  = biome_info.get("thumbnail_url") or BIOME_IMAGES.get(biome_name, "")

        desc = [
            f"**Account:** `{uname}`",
            f"**Biome:** {emoji} {biome_name}",
            f"**Time:** <t:{unix_ts}:F> (<t:{unix_ts}:R>)",
        ]
        if ps_link:
            desc.append(f"**[🔗 Join Server]({ps_link})**")

        embed = {
            "title":       f"{emoji}  Biome Alert — {biome_name}",
            "description": "\n".join(desc),
            "color":       color_int,
            "footer":      {"text": f"MultiFInstance v{VERSION}"},
            "timestamp":   time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        if thumb_url:
            embed["thumbnail"] = {"url": thumb_url}

        payload = {"embeds": [embed]}
        if ping:
            payload["content"] = ping

        threading.Thread(target=self._post_webhook,
                         args=(wh, payload), daemon=True).start()

    def _send_macro_status_webhooks(self, status):
        """
        Send macro started/stopped embed to each configured webhook.
        Each webhook only sees the accounts it is configured to receive
        (its targets list), and only those that are currently active
        (have a live log file). This is the "active accounts on THIS webhook"
        feature — every webhook gets a personalised embed.
        """
        unix_ts = int(time.time())

        def _is_active(uname):
            if not uname or not self._detection_mgr:
                return False
            return bool(self._detection_mgr._get_log_for_user(uname))

        def _fmt(names):
            return ", ".join(f"`{n}`" for n in names) if names else "None"

        def _send(url, relevant_names):
            """Build and post an embed that only lists relevant_names."""
            active_on_wh   = [n for n in relevant_names if _is_active(n)]
            inactive_on_wh = [n for n in relevant_names if not _is_active(n)]

            if active_on_wh:
                active_str = _fmt(active_on_wh)
            else:
                active_str = "None detected"
            if inactive_on_wh:
                inactive_str = f"\n**Offline:** {_fmt(inactive_on_wh)}"
            else:
                inactive_str = ""

            if status == "started":
                payload = {"embeds": [{
                    "title":       "▶  Macro Started",
                    "description": (
                        f"**Active Accounts on this webhook:** {active_str}"
                        f"{inactive_str}\n"
                        f"**Time:** <t:{unix_ts}:F>"
                    ),
                    "color":       0x5865f2,
                    "footer":      {"text": f"MultiFInstance v{VERSION}"},
                    "timestamp":   time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                }]}
            else:
                payload = {"embeds": [{
                    "title":       "■  Macro Stopped",
                    "description": (
                        f"**Active Accounts on this webhook:** {active_str}"
                        f"{inactive_str}\n"
                        f"**Time:** <t:{unix_ts}:F>"
                    ),
                    "color":       0xe05068,
                    "footer":      {"text": f"MultiFInstance v{VERSION}"},
                    "timestamp":   time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                }]}
            threading.Thread(target=self._post_webhook, args=(url, payload), daemon=True).start()

        all_names = [a.get("roblox_username", "") for a in self.accounts
                     if a.get("roblox_username")]

        for wh in self.webhooks:
            url = wh.get("url", "").strip()
            if not url:
                continue
            targets = wh.get("targets", ["all"])
            if "all" in targets:
                relevant = all_names
            else:
                relevant = [n for n in all_names if n.lower() in
                            [t.lower() for t in targets]]
            _send(url, relevant)

        seen_urls = {wh.get("url", "").strip() for wh in self.webhooks}
        for acct in self.accounts:
            acct_wh = acct.get("discord_webhook", "").strip()
            uname   = acct.get("roblox_username", "")
            if acct_wh and uname and acct_wh not in seen_urls:
                _send(acct_wh, [uname])
                seen_urls.add(acct_wh)
    def _post_webhook(self, url, payload):
        try:
            clean = {k: v for k, v in payload.items() if v is not None}
            data  = json.dumps(clean).encode("utf-8")
            req   = urllib.request.Request(
                url, data=data,
                headers={"Content-Type": "application/json",
                         "User-Agent": "DiscordBot (https://github.com/pws32z, 1)"},
                method="POST")
            try:
                with urllib.request.urlopen(req, timeout=10) as r:
                    status = r.getcode()
            except urllib.error.HTTPError as he:
                status = he.code
                try:
                    body = he.read().decode("utf-8", errors="replace")
                except Exception:
                    body = ""
                print(f"[Webhook] HTTP {status}: {body[:200]}")
                self.root.after(0, lambda s=status, b=body:
                    self._toast(f"⚠  HTTP {s}: {b[:80]}"))
                self.root.after(0, lambda s=status, b=body:
                    self._log_activity(f"⚠ Webhook HTTP {s}: {b[:120]}"))
                return
            if status in (200, 204):
                print(f"[Webhook] Sent OK (HTTP {status})")
                self.root.after(0, lambda: self._toast("✓  Webhook sent"))
                self.root.after(0, lambda: self._log_activity("✓ Webhook sent OK"))
            else:
                print(f"[Webhook] Unexpected status {status}")
                self.root.after(0, lambda s=status: self._toast(f"⚠  Webhook error {s}"))
        except Exception as ex:
            print(f"[Webhook] Exception: {ex}")
            self.root.after(0, lambda e=str(ex): self._toast(f"⚠  {e[:80]}"))
            self.root.after(0, lambda e=str(ex): self._log_activity(f"⚠ Webhook error: {e[:120]}"))


    def _save_config(self):
        for inst in self.instances:
            for vk, dk in [("roblox_username_var", "roblox_username"),
                           ("private_server_var",  "private_server"),
                           ("discord_webhook_var", "discord_webhook")]:
                if vk in inst:
                    inst[dk] = inst[vk].get().strip()

        data = {
            "version":        VERSION,
            "discord_user_id": self.discord_user_id.get().strip(),
            "accounts": self.accounts,
            "webhooks": self.webhooks,
            "instances": [
                {"id":              i["id"],
                 "roblox_username": i.get("roblox_username", ""),
                 "private_server":  i.get("private_server", ""),
                 "discord_webhook": i.get("discord_webhook", ""),
                 "active":          i.get("active", False)}
                for i in self.instances
                if i.get("roblox_username") or i.get("discord_webhook") or i.get("private_server")
            ],
            "biome_alerts": {n: v.get() for n, v in self.biome_alert_vars.items()},
            "biome_counts": {k: v for k, v in self.biome_counts.items() if v > 0},
            "antiafk": {
                "interval":   self._antiafk_interval.get(),
                "action":     self._antiafk_action.get(),
                "user_safe":  self._antiafk_user_safe.get(),
                "sequential": self._antiafk_sequential.get(),
                "seq_delay":  self._antiafk_seq_delay.get(),
            },
        }
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as ex:
            self._toast(f"⚠  Save failed: {str(ex)[:40]}")

    def _load_config(self):
        if not os.path.exists(CONFIG_FILE):
            return
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return

        self.discord_user_id.set(data.get("discord_user_id", ""))

        saved_accounts = data.get("accounts", [])
        if saved_accounts:
            self.accounts = [a for a in saved_accounts
                             if isinstance(a, dict) and a.get("roblox_username")]

        saved_webhooks = data.get("webhooks", [])
        if saved_webhooks:
            self.webhooks = [w for w in saved_webhooks
                             if isinstance(w, dict) and w.get("url")]

        saved = data.get("instances", [])
        if saved:
            self.instances = [
                {"id":              s.get("id", idx + 1),
                 "roblox_username": s.get("roblox_username", ""),
                 "private_server":  s.get("private_server", ""),
                 "discord_webhook": s.get("discord_webhook", ""),
                 "active":          False}
                for idx, s in enumerate(saved)
            ]

        self._pending_biome_alerts = data.get("biome_alerts", {})

        saved_counts = data.get("biome_counts", {})
        for name, count in saved_counts.items():
            if isinstance(count, int) and count > 0:
                self.biome_counts[name] = self.biome_counts.get(name, 0) + count

        afk = data.get("antiafk", {})
        if afk:
            self._antiafk_interval.set(afk.get("interval",  120))
            self._antiafk_action.set(  afk.get("action",   "space"))
            self._antiafk_user_safe.set(afk.get("user_safe", False))
            self._antiafk_sequential.set(afk.get("sequential", False))
            self._antiafk_seq_delay.set(afk.get("seq_delay", 0.75))

    def _save_alerts(self):
        self._save_config()
        everyone = [n for n, v in self.biome_alert_vars.items() if v.get() == "@everyone"]
        forced   = [n for n, _, ae, *__ in BIOMES if ae]
        self._toast(f"✓  Saved — {len(everyone)+len(forced)} biomes will @everyone")


    def _load_avatar_small(self, inst, canvas, size=28):
        if not canvas:
            return
        try:
            uname = inst.get("roblox_username", "").strip()
            if not uname:
                return
            url  = "https://users.roblox.com/v1/usernames/users"
            body = json.dumps({"usernames": [uname], "excludeBannedUsers": False}).encode()
            req  = urllib.request.Request(
                url, data=body, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=6) as r:
                resp = json.loads(r.read())
            users = resp.get("data", [])
            if not users:
                return
            uid = users[0]["id"]

            thumb_url = (f"https://thumbnails.roblox.com/v1/users/avatar-headshot"
                         f"?userIds={uid}&size=48x48&format=Png&isCircular=true")
            with urllib.request.urlopen(thumb_url, timeout=6) as r:
                td = json.loads(r.read())
            img_url = td["data"][0]["imageUrl"]
            with urllib.request.urlopen(img_url, timeout=6) as r:
                img_bytes = r.read()

            if PIL_AVAILABLE:
                img   = Image.open(io.BytesIO(img_bytes)).resize((size, size), Image.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                inst["_avatar_photo"] = photo
                def _up():
                    try:
                        canvas.delete("all")
                        canvas.create_image(0, 0, anchor="nw", image=photo)
                    except Exception:
                        pass
                self.root.after(0, _up)
            else:
                initial = (uname or "?")[0].upper()
                def _up_fallback():
                    try:
                        canvas.delete("all")
                        canvas.create_rectangle(0, 0, size, size,
                                                fill=ACCENT_DIM, outline=ACCENT)
                        canvas.create_text(size//2, size//2, text=initial,
                                           fill=ACCENT, font=("Segoe UI", 9, "bold"))
                    except Exception:
                        pass
                self.root.after(0, _up_fallback)
        except Exception:
            pass


    def _refresh_log_frame(self):
        try:
            active_accounts = []
            for acct in self.accounts:
                uname = acct.get("roblox_username", "").strip()
                if not uname:
                    continue
                active = False
                if self._detection_mgr:
                    if self._detection_mgr._get_log_for_user(uname):
                        active = True
                    if not active and WIN32_AVAILABLE:
                        pid = self._detection_mgr.username_pid_map.get(uname.lower())
                        if pid:
                            try:
                                import psutil as _psutil
                                if _psutil.pid_exists(pid):
                                    active = True
                            except Exception:
                                active = True
                if active:
                    active_accounts.append(acct)

            current_names = [a.get("roblox_username", "") for a in active_accounts]
            self._online_badge.config(text=f"{len(active_accounts)} online")

            if current_names == self._last_active_usernames:
                self._update_biome_labels_inplace()
                return

            self._last_active_usernames = current_names

            for w in self._log_frame.winfo_children():
                w.destroy()

            if not active_accounts:
                lbl(self._log_frame, "No active accounts",
                    fg=TEXT_FAINT, bg=BG_CARD, font=("Segoe UI", 8),
                    pady=6).pack(anchor="w", padx=8)
                return

            self._biome_label_map = {}

            for acct in active_accounts:
                uname = acct.get("roblox_username", "—")
                ps    = acct.get("private_server", "").strip()

                row = fr(self._log_frame, bg=BG_ITEM)
                row.config(highlightthickness=1, highlightbackground=BORDER_ITEM)
                row.pack(fill="x", pady=2)

                av_cv = tk.Canvas(row, width=32, height=32, bg=BG_ITEM,
                                  highlightthickness=0, bd=0)

                cached = self._avatar_cache.get(uname)
                if cached:
                    av_cv.create_image(0, 0, anchor="nw", image=cached)
                else:
                    av_cv.create_oval(1, 1, 31, 31, fill=ACCENT_DIM, outline=ACCENT)
                    av_cv.create_text(16, 16,
                                      text=uname[0].upper() if uname else "?",
                                      fill=TEXT_PRIMARY,
                                      font=("Segoe UI", 10, "bold"), tags="ph")
                    threading.Thread(
                        target=self._fetch_and_cache_avatar,
                        args=(uname, 32), daemon=True).start()

                av_cv.pack(side="left", padx=(6, 6), pady=4)

                if uname not in self._avatar_canvas_registry:
                    self._avatar_canvas_registry[uname] = []
                self._avatar_canvas_registry[uname].append(av_cv)

                dot_cv = tk.Canvas(row, width=8, height=8, bg=BG_ITEM,
                                   highlightthickness=0)
                dot_cv.create_oval(1, 1, 7, 7, fill="#22c55e", outline="")
                dot_cv.pack(side="left", padx=(0, 6))

                lbl(row, uname, fg=TEXT_PRIMARY, bg=BG_ITEM,
                    font=("Segoe UI", 9, "bold")).pack(side="left")

                biome_lbl = lbl(row, "", fg=TEXT_MUTED, bg=BG_ITEM,
                                font=("Segoe UI", 7))
                biome_lbl.pack(side="left")
                self._biome_label_map[uname] = biome_lbl
                self._update_biome_label(uname, biome_lbl)

                if ps:
                    jb = lbl(row, "🔗 Join", fg=ACCENT, bg=BG_ITEM,
                             font=("Segoe UI", 7), cursor="hand2", padx=6)
                    jb.pack(side="right", pady=4)
                    jb.bind("<Button-1>", lambda e, link=ps: webbrowser.open(link))
        except Exception:
            pass

    def _update_biome_label(self, uname, label_widget):
        """Update a single biome label widget from current detection state."""
        try:
            biome = ""
            if self._detection_mgr:
                biome = self._detection_mgr.account_biomes.get(uname, "")
            if biome and biome != "NORMAL":
                binfo = BIOME_DATA.get(biome, {})
                emoji = binfo.get("emoji", "")
                label_widget.config(text=f"  {emoji} {biome}")
            else:
                label_widget.config(text="")
        except Exception:
            pass

    def _update_biome_labels_inplace(self):
        """Refresh only biome text labels without touching anything else."""
        try:
            for uname, lbl_widget in getattr(self, "_biome_label_map", {}).items():
                self._update_biome_label(uname, lbl_widget)
        except Exception:
            pass

    def _fetch_and_cache_avatar(self, username, size=32):
        """
        Fetch Roblox headshot, store in self._avatar_cache, then update
        every canvas registered for this username — no re-fetch ever needed.
        """
        if not username or not PIL_AVAILABLE:
            return
        if username in self._avatar_cache:
            return
        try:
            url  = "https://users.roblox.com/v1/usernames/users"
            body = json.dumps({"usernames": [username],
                               "excludeBannedUsers": False}).encode()
            req  = urllib.request.Request(
                url, data=body, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=8) as r:
                users = json.loads(r.read()).get("data", [])
            if not users:
                return
            uid = users[0]["id"]

            thumb_url = (f"https://thumbnails.roblox.com/v1/users/avatar-headshot"
                         f"?userIds={uid}&size=60x60&format=Png&isCircular=true")
            with urllib.request.urlopen(thumb_url, timeout=8) as r:
                img_url = json.loads(r.read())["data"][0]["imageUrl"]
            with urllib.request.urlopen(img_url, timeout=8) as r:
                img_bytes = r.read()

            img   = Image.open(io.BytesIO(img_bytes)).resize((size, size), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)

            self._avatar_cache[username] = photo

            def _apply():
                try:
                    for cv in self._avatar_canvas_registry.get(username, []):
                        try:
                            cv.delete("all")
                            cv.create_image(0, 0, anchor="nw", image=photo)
                        except Exception:
                            pass
                except Exception:
                    pass
            self.root.after(0, _apply)
        except Exception:
            pass

    def _load_avatar_into_canvas(self, username, canvas, size=32):
        """
        Compatibility shim used by the Accounts page cards.
        Uses the shared cache — fetches once, updates instantly if already cached.
        """
        if not username:
            return
        cached = self._avatar_cache.get(username)
        if cached:
            def _draw():
                try:
                    canvas.delete("all")
                    canvas.create_image(0, 0, anchor="nw", image=cached)
                except Exception:
                    pass
            self.root.after(0, _draw)
            return
        if username not in self._avatar_canvas_registry:
            self._avatar_canvas_registry[username] = []
        self._avatar_canvas_registry[username].append(canvas)
        self._fetch_and_cache_avatar(username, size)

    def _refresh_instance_chips(self):
        try:
            total  = len(self.accounts)
            active = 0
            if self._detection_mgr:
                for acct in self.accounts:
                    uname = acct.get("roblox_username", "").strip()
                    if uname and self._detection_mgr._get_log_for_user(uname):
                        active += 1
            self._inst_chip.config(text=f"{total} account{'s' if total != 1 else ''}")
            self._active_chip.config(
                text=f"  {active} active",
                fg=ACCENT if active > 0 else TEXT_FAINT,
                bg=ACCENT_DIM if active > 0 else BG_CARD,
            )
        except Exception:
            pass
    def _reset_biome_counts(self):
        for name in list(self.biome_counts.keys()):
            self.biome_counts[name] = 0
        for name in BIOME_DATA:
            self.biome_counts.setdefault(name, 0)
        try:
            for name, lw in self._biome_count_labels.items():
                lw.config(text="0", fg=TEXT_MUTED)
        except Exception:
            pass
        self._log_activity("⟳ Biome counts reset")
        self._toast("⟳  Biome counts reset")
        self._save_config()

    def _animate_pulse(self, canvas, step=0):
        try:
            if self.running:
                colors = [ACCENT, "#00cc8a", "#009e6e", "#00cc8a"]
            else:
                colors = [RED, "#c04060", "#a03050", "#c04060"]
            canvas.itemconfig("dot", fill=colors[step % len(colors)])
            canvas.after(450, lambda: self._animate_pulse(canvas, step + 1))
        except Exception:
            pass


    def _toast(self, msg):
        try:
            if self._toast_win:
                try: self._toast_win.destroy()
                except Exception: pass
                self._toast_win = None

            t = tk.Toplevel(self.root)
            t.wm_overrideredirect(True)
            t.attributes("-topmost", True)
            if sys.platform == "win32":
                try: t.attributes("-alpha", 0.0)
                except Exception: pass
            self.root.update_idletasks()

            if any(w in msg for w in ("⚠", "✕", "failed", "error", "Error")):
                bg_col, fg_col, bar_col = RED_BG, RED, RED
            elif any(w in msg for w in ("✓", "💾", "saved", "✔")):
                bg_col, fg_col, bar_col = "#0d1f13", "#22c55e", "#22c55e"
            else:
                bg_col, fg_col, bar_col = "#0d1020", TEXT_PRIMARY, ACCENT

            outer = tk.Frame(t, bg=bg_col, bd=0,
                             highlightthickness=1, highlightbackground=bar_col)
            outer.pack()
            bar_f = tk.Frame(outer, bg=bar_col, width=3)
            bar_f.pack(side="left", fill="y")
            inner = tk.Label(outer, text=msg, fg=fg_col, bg=bg_col,
                             font=("Segoe UI", 9, "bold"), padx=16, pady=9)
            inner.pack(side="left")

            t.update_idletasks()
            tw, th = t.winfo_reqwidth(), t.winfo_reqheight()
            rx = self.root.winfo_rootx()
            ry = self.root.winfo_rooty()
            rw = self.root.winfo_width()
            rh = self.root.winfo_height()

            final_y = ry + rh - th - 22
            start_y = final_y + 20
            t.wm_geometry(f"+{rx+(rw-tw)//2}+{start_y}")
            self._toast_win = t

            STEPS = 12
            def _slide_in(step=0):
                if not _ANIM_ROOT or step > STEPS:
                    return
                try:
                    ease = 1.0 - (1.0 - step / STEPS) ** 2
                    cy = int(start_y + (final_y - start_y) * ease)
                    t.wm_geometry(f"+{rx+(rw-tw)//2}+{cy}")
                    if sys.platform == "win32":
                        t.attributes("-alpha", min(1.0, ease + 0.1))
                except Exception:
                    return
                if step < STEPS:
                    _ANIM_ROOT.after(12, lambda: _slide_in(step + 1))
            _slide_in()

            t.after(2200, lambda: self._close_toast(t))
        except Exception:
            pass

    def _close_toast(self, t):
        """Fade-out the toast before destroying."""
        if sys.platform == "win32":
            def _fade(step=0, steps=8):
                if not _ANIM_ROOT:
                    try: t.destroy()
                    except Exception: pass
                    return
                try:
                    alpha = max(0.0, 1.0 - step / steps)
                    t.attributes("-alpha", alpha)
                except Exception:
                    pass
                if step >= steps:
                    try: t.destroy()
                    except Exception: pass
                    if self._toast_win is t:
                        self._toast_win = None
                else:
                    _ANIM_ROOT.after(30, lambda: _fade(step + 1))
            _fade()
        else:
            try: t.destroy()
            except Exception: pass
            if self._toast_win is t:
                self._toast_win = None


    def _show_tip(self, widget, text):
        self._hide_tip()
        try:
            x = widget.winfo_rootx() + 50
            y = widget.winfo_rooty() + 4
            self._tip_win = tk.Toplevel(self.root)
            self._tip_win.wm_overrideredirect(True)
            self._tip_win.wm_geometry(f"+{x}+{y}")
            tk.Label(self._tip_win, text=text, fg=TEXT_PRIMARY, bg=BG_CARD,
                     font=("Segoe UI", 8), padx=8, pady=4,
                     highlightthickness=1, highlightbackground=BORDER).pack()
        except Exception:
            pass

    def _hide_tip(self):
        try:
            if self._tip_win:
                self._tip_win.destroy()
                self._tip_win = None
        except Exception:
            pass


    def _on_close(self):
        self._save_config()
        self._kill_singleton_mutex()
        self.root.destroy()


    def _page_accounts(self, parent):
        page = fr(parent, bg=BG_BASE)
        page.columnconfigure(0, weight=1)
        page.rowconfigure(3, weight=1)

        lbl(page, "Accounts", fg=TEXT_PRIMARY, bg=BG_BASE,
            font=("Segoe UI", 15, "bold")).grid(
                row=0, column=0, sticky="w", padx=20, pady=(16, 0))

        sub = fr(page, bg=BG_BASE)
        sub.grid(row=1, column=0, sticky="ew", padx=20, pady=(10, 0))
        sub.columnconfigure(1, weight=1)

        ic = tk.Canvas(sub, width=18, height=20, bg=BG_BASE,
                       highlightthickness=0, bd=0)
        ic.create_oval(4, 1, 14, 11, fill=TEXT_PRIMARY, outline="")
        ic.create_arc(0, 11, 18, 25, start=0, extent=180,
                      fill=TEXT_PRIMARY, outline="")
        ic.pack(side="left", padx=(0, 7))

        lbl(sub, "Accounts Manager", fg=TEXT_PRIMARY, bg=BG_BASE,
            font=("Segoe UI", 11, "bold")).pack(side="left")

        self._acct_count_badge = tk.Label(
            sub, text=f"  {len(self.accounts)} accounts  ",
            fg="#a0a8c0", bg="#1e2236",
            font=("Segoe UI", 8), padx=6, pady=2,
            relief="flat", bd=0)
        self._acct_count_badge.pack(side="left", padx=10)

        add_btn = accent_btn(
            sub, "＋  Add Account",
            command=self._acct_toggle_form,
            padx=14, pady=6)
        add_btn.pack(side="right")

        launch_all_btn = tk.Button(
            sub, text="🚀  Launch All",
            fg="#ffffff", bg="#22c55e",
            font=("Segoe UI", 9, "bold"),
            relief="flat", bd=0, cursor="hand2",
            activebackground="#16a34a", activeforeground="#ffffff",
            highlightthickness=1, highlightbackground="#0f4a20",
            command=self._acct_launch_all,
            padx=14, pady=6)
        launch_all_btn.pack(side="right", padx=(0, 8))
        def _lall_enter(e):
            _anim_bg(launch_all_btn, "#22c55e", "#16a34a", steps=6, delay=7)
            _anim_glow(launch_all_btn, "#0f4a20", "#22c55e", steps=8, delay=7)
        def _lall_leave(e):
            _anim_bg(launch_all_btn, "#16a34a", "#22c55e", steps=6, delay=7)
            _anim_glow(launch_all_btn, "#22c55e", "#0f4a20", steps=8, delay=7)
        def _lall_press(e):
            _anim_bg(launch_all_btn, "#16a34a", "#0f7a36", steps=3, delay=5)
            _pulse_glow(launch_all_btn, "#22c55e", "#86efac", steps=6, delay=5)
        def _lall_release(e): _anim_bg(launch_all_btn, "#0f7a36", "#16a34a", steps=3, delay=5)
        launch_all_btn.bind("<Enter>", _lall_enter)
        launch_all_btn.bind("<Leave>", _lall_leave)
        launch_all_btn.bind("<ButtonPress-1>", _lall_press)
        launch_all_btn.bind("<ButtonRelease-1>", _lall_release)

        lbl(page,
            "Add your Roblox accounts to track (Case insensitive).",
            fg="#6b7494", bg=BG_BASE,
            font=("Segoe UI", 9)).grid(
                row=2, column=0, sticky="w", padx=20, pady=(6, 10))

        sf = ScrollFrame(page, bg=BG_BASE)
        sf.grid(row=3, column=0, sticky="nsew", padx=14, pady=(0, 8))
        self._acct_sf    = sf
        self._acct_inner = sf.inner
        self._acct_inner.columnconfigure(0, weight=1)

        FORM_BG     = "#13172a"
        FORM_BORDER = "#4a4dcc"

        form_outer = tk.Frame(self._acct_inner, bg=FORM_BG, bd=0,
                              highlightthickness=1,
                              highlightbackground=FORM_BORDER)
        form_outer.columnconfigure(0, weight=1)
        self._acct_form_card = form_outer
        form_outer.grid(row=0, column=0, sticky="ew", pady=(0, 12))

        lbl(form_outer, "Add New Account", fg=TEXT_PRIMARY, bg=FORM_BG,
            font=("Segoe UI", 10, "bold")).grid(
                row=0, column=0, sticky="w", padx=18, pady=(16, 10))

        fields = tk.Frame(form_outer, bg=FORM_BG)
        fields.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 8))
        fields.columnconfigure(0, weight=1)
        fields.columnconfigure(1, weight=1)

        ENTRY_BG = "#0d1120"
        ENTRY_BD = "#2a2f4a"

        ucol = tk.Frame(fields, bg=FORM_BG)
        ucol.grid(row=0, column=0, sticky="ew", padx=(0, 16))
        tk.Label(ucol, text="Username", fg="#8892b0", bg=FORM_BG,
                 font=("Segoe UI", 8, "bold"), anchor="w").pack(anchor="w", pady=(0, 5))
        self._acct_uname_var = tk.StringVar()
        uent = tk.Entry(ucol, textvariable=self._acct_uname_var,
                        bg=ENTRY_BG, fg="#5a6280",
                        insertbackground=TEXT_PRIMARY,
                        relief="flat", font=("Segoe UI", 9),
                        highlightthickness=1, highlightbackground=ENTRY_BD,
                        highlightcolor="#5c5fe8")
        uent.insert(0, "Roblox Username")
        uent.pack(fill="x", ipady=7)

        def _uf_in(e):
            if uent.get() == "Roblox Username":
                uent.delete(0, "end"); uent.config(fg=TEXT_MUTED)
        def _uf_out(e):
            if not uent.get().strip():
                uent.insert(0, "Roblox Username"); uent.config(fg="#5a6280")
        uent.bind("<FocusIn>", _uf_in); uent.bind("<FocusOut>", _uf_out)

        pcol = tk.Frame(fields, bg=FORM_BG)
        pcol.grid(row=0, column=1, sticky="ew")
        tk.Label(pcol, text="Private Server Link", fg="#8892b0", bg=FORM_BG,
                 font=("Segoe UI", 8, "bold"), anchor="w").pack(anchor="w", pady=(0, 5))
        self._acct_ps_var = tk.StringVar()
        pent = tk.Entry(pcol, textvariable=self._acct_ps_var,
                        bg=ENTRY_BG, fg="#5a6280",
                        insertbackground=TEXT_PRIMARY,
                        relief="flat", font=("Segoe UI", 9),
                        highlightthickness=1, highlightbackground=ENTRY_BD,
                        highlightcolor="#5c5fe8")
        pent.insert(0, "https://www.roblox.com/games/...")
        pent.pack(fill="x", ipady=7)

        def _pf_in(e):
            if pent.get() == "https://www.roblox.com/games/...":
                pent.delete(0, "end"); pent.config(fg=TEXT_MUTED)
        def _pf_out(e):
            if not pent.get().strip():
                pent.insert(0, "https://www.roblox.com/games/..."); pent.config(fg="#5a6280")
        pent.bind("<FocusIn>", _pf_in); pent.bind("<FocusOut>", _pf_out)

        crow = tk.Frame(fields, bg=FORM_BG)
        crow.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))

        ck_hdr = tk.Frame(crow, bg=FORM_BG)
        ck_hdr.pack(fill="x")
        tk.Label(ck_hdr, text=".ROBLOSECURITY Cookie",
                 fg="#8892b0", bg=FORM_BG,
                 font=("Segoe UI", 8, "bold")).pack(side="left", pady=(0, 4))
        tk.Label(ck_hdr,
                 text="  F12 → Application → Cookies → www.roblox.com → .ROBLOSECURITY → copy Value",
                 fg=TEXT_FAINT, bg=FORM_BG,
                 font=("Segoe UI", 7)).pack(side="left", padx=(6, 0), pady=(0, 4))

        self._acct_cookie_var = tk.StringVar()
        cent = tk.Entry(crow, textvariable=self._acct_cookie_var,
                        bg=ENTRY_BG, fg="#5a6280",
                        insertbackground=TEXT_PRIMARY,
                        relief="flat", font=("Segoe UI", 9),
                        highlightthickness=1, highlightbackground=ENTRY_BD,
                        highlightcolor="#5c5fe8",
                        show="•")
        cent.insert(0, "Paste .ROBLOSECURITY value here…")
        cent.pack(fill="x", ipady=7)

        _cookie_shown = [False]
        def _toggle_cookie_vis():
            _cookie_shown[0] = not _cookie_shown[0]
            cent.config(show="" if _cookie_shown[0] else "•")
            show_toggle.config(text="🙈 Hide" if _cookie_shown[0] else "👁 Show")
        show_toggle = tk.Label(crow, text="👁 Show", fg=TEXT_FAINT, bg=FORM_BG,
                               font=("Segoe UI", 7), cursor="hand2")
        show_toggle.pack(anchor="e", pady=(3, 0))
        show_toggle.bind("<Button-1>", lambda e: _toggle_cookie_vis())
        show_toggle.bind("<Enter>", lambda e: show_toggle.config(fg=ACCENT))
        show_toggle.bind("<Leave>", lambda e: show_toggle.config(fg=TEXT_FAINT))

        warn_row = tk.Frame(crow, bg="#1f1205",
                            highlightthickness=1, highlightbackground="#7c3a00")
        warn_row.pack(fill="x", pady=(6, 0))
        tk.Label(warn_row,
                 text="⚠  Never share your .ROBLOSECURITY cookie with anyone. "
                      "It gives full access to your Roblox account.",
                 fg="#f97316", bg="#1f1205",
                 font=("Segoe UI", 8, "bold"),
                 wraplength=520, justify="left",
                 padx=10, pady=6).pack(anchor="w")

        def _cf_in(e):
            if cent.get() == "Paste .ROBLOSECURITY value here…":
                cent.delete(0, "end"); cent.config(fg=TEXT_MUTED)
        def _cf_out(e):
            if not cent.get().strip():
                cent.insert(0, "Paste .ROBLOSECURITY value here…"); cent.config(fg="#5a6280")
        cent.bind("<FocusIn>", _cf_in); cent.bind("<FocusOut>", _cf_out)

        wcol = tk.Frame(fields, bg=FORM_BG)
        wcol.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        tk.Label(wcol, text="Discord Webhook URL (Optional)",
                 fg="#8892b0", bg=FORM_BG,
                 font=("Segoe UI", 8, "bold"), anchor="w").pack(anchor="w", pady=(0, 5))
        self._acct_wh_var = tk.StringVar()
        went = tk.Entry(wcol, textvariable=self._acct_wh_var,
                        bg=ENTRY_BG, fg="#5a6280",
                        insertbackground=TEXT_PRIMARY,
                        relief="flat", font=("Segoe UI", 9),
                        highlightthickness=1, highlightbackground=ENTRY_BD,
                        highlightcolor="#5c5fe8")
        went.insert(0, "https://discord.com/api/webhooks/...")
        went.pack(fill="x", ipady=7)

        def _wf_in(e):
            if went.get() == "https://discord.com/api/webhooks/...":
                went.delete(0, "end"); went.config(fg=TEXT_MUTED)
        def _wf_out(e):
            if not went.get().strip():
                went.insert(0, "https://discord.com/api/webhooks/..."); went.config(fg="#5a6280")
        went.bind("<FocusIn>", _wf_in); went.bind("<FocusOut>", _wf_out)

        btn_row = tk.Frame(form_outer, bg=FORM_BG)
        btn_row.grid(row=2, column=0, sticky="e", padx=18, pady=(6, 16))

        cancel_b = icon_btn(
            btn_row, "Cancel",
            fg=TEXT_MUTED, bg=BG_ITEM,
            hover_fg=RED, hover_bg=RED_BG,
            font=("Segoe UI", 9),
            command=self._acct_hide_form, padx=14, pady=6)
        cancel_b.pack(side="left", padx=(0, 10))

        confirm_b = accent_btn(
            btn_row, "✓  Add Account",
            command=lambda *_: self._acct_confirm(uent, pent),
            padx=14, pady=6)
        confirm_b.pack(side="left")

        self._acct_list_frame = fr(self._acct_inner, bg=BG_BASE)
        self._acct_list_frame.grid(row=1, column=0, sticky="ew")
        self._acct_list_frame.columnconfigure(0, weight=1)
        self._acct_refresh_list()
        return page

    def _acct_toggle_form(self):
        try:
            if self._acct_form_card.winfo_viewable():
                self._acct_hide_form()
            else:
                self._acct_show_form()
        except Exception:
            self._acct_show_form()

    def _acct_show_form(self):
        try:
            self._acct_form_card.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        except Exception:
            pass

    def _acct_hide_form(self):
        try:
            self._acct_form_card.grid_remove()
        except Exception:
            pass

    def _acct_confirm(self, uent, pent):
        uname = uent.get().strip()
        ps    = pent.get().strip()
        wh    = getattr(self, "_acct_wh_var", None)
        wh    = wh.get().strip() if wh else ""
        cookie_var = getattr(self, "_acct_cookie_var", None)
        cookie = cookie_var.get().strip() if cookie_var else ""
        if cookie == "Paste cookie value here…":
            cookie = ""
        if not uname or uname == "Roblox Username":
            uent.config(highlightbackground=RED)
            return
        uent.config(highlightbackground=BORDER_ITEM)
        if ps == "https://www.roblox.com/games/..." or not ps or not ps.startswith("http"):
            pent.config(highlightbackground=RED)
            self._toast("⚠  Private Server URL is required")
            return
        pent.config(highlightbackground=BORDER_ITEM)
        if wh == "https://discord.com/api/webhooks/...":
            wh = ""
        self.accounts.append({"roblox_username": uname, "private_server": ps,
                               "discord_webhook": wh, "roblosecurity": cookie})
        self._acct_hide_form()
        self._acct_refresh_list()
        self._save_config()
        if self._detection_mgr:
            self._detection_mgr.reset()
        self._toast(f"✓  Account '{uname}' added")

    def _acct_remove(self, idx):
        if 0 <= idx < len(self.accounts):
            name = self.accounts.pop(idx)["roblox_username"]
            self._acct_refresh_list()
            self._save_config()
            if self._detection_mgr:
                self._detection_mgr.reset()
            self._toast(f"✕  Removed '{name}'")

    def _acct_launch_all(self):
        """Launch every account into its own private server using its cookie."""
        if not self.accounts:
            self._toast("⚠  No accounts to launch")
            return
        valid = [a for a in self.accounts if a.get("private_server", "").startswith("http")]
        if not valid:
            self._toast("⚠  No accounts have a valid Private Server URL")
            return
        no_cookie = [a["roblox_username"] for a in valid if not a.get("roblosecurity", "").strip()]
        if no_cookie:
            self._toast(f"⚠  Missing cookie for: {', '.join(no_cookie[:3])}")

        total = len(valid)
        self.root.after(0, lambda: self._log_activity(
            f"🚀 Launching all {total} account(s)…"))

        def _open_all():
            for i, acct in enumerate(valid):
                uname  = acct.get("roblox_username", f"Account {i+1}")
                url    = acct["private_server"]
                cookie = acct.get("roblosecurity", "").strip()

                h = self._hold_singleton_mutex()
                self.root.after(0, lambda n=i+1, hv=h:
                    self._log_activity(f"🔒 Mutex held (handle={hv}) for instance {n}"))

                self.root.after(0, lambda u=uname, n=i+1, t=total:
                    self._log_activity(f"🚀 Launching account {n}/{t}: {u}"))
                self.root.after(0, lambda u=uname, n=i+1, t=total:
                    self._toast(f"🚀  Launching {u} ({n}/{t})…"))

                self._launch_account_with_cookie(uname, url, cookie, threaded=False)

                if i < total - 1:
                    time.sleep(6)

            self.root.after(0, lambda: self._toast(f"✓  All {total} accounts launched"))
            self.root.after(0, lambda: self._log_activity(
                f"✓ All {total} accounts launched"))

        threading.Thread(target=_open_all, daemon=True).start()
        self._toast(f"🚀  Launching {total} account(s)…")

    def _find_chrome_exe(self):
        """Find Chrome, Chromium, or Edge executable on Windows."""
        local  = os.environ.get("LOCALAPPDATA", "")
        prog   = os.environ.get("PROGRAMFILES", "")
        prog86 = os.environ.get("PROGRAMFILES(X86)", "")
        for base in [local, prog, prog86]:
            for rel in [
                r"Google\Chrome\Application\chrome.exe",
                r"Google\Chrome Beta\Application\chrome.exe",
                r"Chromium\Application\chrome.exe",
                r"Microsoft\Edge\Application\msedge.exe",
            ]:
                p = os.path.join(base, rel)
                if os.path.isfile(p):
                    return p
        try:
            import winreg
            for root_key in [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]:
                for key_path in [
                    r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe",
                    r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe",
                ]:
                    try:
                        with winreg.OpenKey(root_key, key_path) as k:
                            val, _ = winreg.QueryValueEx(k, "")
                            if val and os.path.isfile(val):
                                return val
                    except OSError:
                        pass
        except Exception:
            pass
        return None

    def _write_cookie_to_profile(self, profile_dir, cookie_value):
        """
        Write .ROBLOSECURITY into a Chrome profile's Cookies SQLite DB.
        Chrome reads this on startup so the account is pre-logged-in.
        Returns True on success.
        """
        import sqlite3
        os.makedirs(os.path.join(profile_dir, "Default"), exist_ok=True)
        db_path = os.path.join(profile_dir, "Default", "Cookies")
        try:
            con = sqlite3.connect(db_path)
            cur = con.cursor()
            cur.execute("""CREATE TABLE IF NOT EXISTS cookies (
                creation_utc     INTEGER NOT NULL UNIQUE PRIMARY KEY,
                host_key         TEXT NOT NULL,
                top_frame_site_key TEXT NOT NULL DEFAULT \'\',
                name             TEXT NOT NULL,
                value            TEXT NOT NULL,
                encrypted_value  BLOB NOT NULL DEFAULT \'\',
                path             TEXT NOT NULL,
                expires_utc      INTEGER NOT NULL,
                is_secure        INTEGER NOT NULL,
                is_httponly      INTEGER NOT NULL,
                last_access_utc  INTEGER NOT NULL,
                has_expires      INTEGER NOT NULL DEFAULT 1,
                is_persistent    INTEGER NOT NULL DEFAULT 1,
                priority         INTEGER NOT NULL DEFAULT 1,
                samesite         INTEGER NOT NULL DEFAULT -1,
                source_scheme    INTEGER NOT NULL DEFAULT 0,
                source_port      INTEGER NOT NULL DEFAULT -1,
                last_update_utc  INTEGER NOT NULL DEFAULT 0,
                source_type      INTEGER NOT NULL DEFAULT 0,
                has_cross_site_ancestor INTEGER NOT NULL DEFAULT 0
            )""")
            now_us = int((time.time() + 11644473600) * 1_000_000)
            exp_us = now_us + 365 * 24 * 3600 * 1_000_000
            cur.execute("DELETE FROM cookies WHERE name=\'.ROBLOSECURITY\'")
            cur.execute(
                """INSERT INTO cookies
                   (creation_utc, host_key, top_frame_site_key, name, value,
                    encrypted_value, path, expires_utc, is_secure, is_httponly,
                    last_access_utc, has_expires, is_persistent, priority,
                    samesite, source_scheme, source_port, last_update_utc)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (now_us, ".roblox.com", "", ".ROBLOSECURITY", cookie_value,
                 b"", "/", exp_us, 1, 1,
                 now_us, 1, 1, 1,
                 -1, 2, 443, now_us),
            )
            con.commit()
            con.close()
            return True
        except Exception as ex:
            self.root.after(0, lambda e=str(ex): self._log_activity(
                f"⚠ Cookie DB error: {e}"))
            return False

    def _launch_account_with_cookie(self, username, private_server_url, cookie, threaded=True):
        """
        Open a dedicated Chrome profile pre-loaded with this account's
        .ROBLOSECURITY cookie, then navigate to the private server URL.

        Each account gets its own profile folder:
            <script_dir>/chrome_profiles/<username>/
        so accounts never share sessions or interfere with each other.

        Flow:
          1. Find Chrome/Edge.
          2. Create/reuse a per-account Chrome profile dir (completely isolated).
          3. Inject the .ROBLOSECURITY cookie into the profile's SQLite Cookies DB.
          4. Launch Chrome with --user-data-dir pointing at that profile and the
             private server URL as the start page — each in a NEW browser process
             (--no-process-singleton) so multiple accounts launch simultaneously.
          5. Chrome opens Roblox.com already logged-in as that account, which
             triggers the Roblox launcher to join the correct private server.
        """
        def _do():
            if not cookie or cookie in ("Paste .ROBLOSECURITY value here…", ""):
                self.root.after(0, lambda: (
                    webbrowser.open(private_server_url),
                    self._toast(f"⚠️  No cookie for {username} — opened in default browser"),
                    self._log_activity(f"⚠ No cookie for {username}, opened default browser"),
                ))
                return

            chrome = self._find_chrome_exe()
            if not chrome:
                self.root.after(0, lambda: (
                    webbrowser.open(private_server_url),
                    self._toast("⚠️  Chrome not found — opened in default browser"),
                    self._log_activity(f"⚠ Chrome not found for {username}, used default browser"),
                ))
                return

            profiles_root = os.path.join(_BASE_DIR, "chrome_profiles")
            safe_name   = re.sub(r"[^\w\-]", "_", username)
            profile_dir = os.path.join(profiles_root, safe_name)
            os.makedirs(os.path.join(profile_dir, "Default"), exist_ok=True)

            ok = self._write_cookie_to_profile(profile_dir, cookie.strip())
            status = "🔑 Cookie injected" if ok else "⚠ Cookie injection failed (Chrome will prompt login)"
            self.root.after(0, lambda s=status: self._log_activity(f"{s} for {username}"))

            try:
                import winreg
                key_path = r"Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\roblox\OpenWithList"
                key = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, key_path,
                                         0, winreg.KEY_SET_VALUE)
                winreg.SetValueEx(key, "MRUList", 0, winreg.REG_SZ, "a")
                winreg.SetValueEx(key, "a",       0, winreg.REG_SZ, "RobloxPlayerLauncher.exe")
                winreg.CloseKey(key)
                uc_path = r"Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\roblox\UserChoice"
                uc_key  = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, uc_path,
                                              0, winreg.KEY_SET_VALUE)
                winreg.SetValueEx(uc_key, "ProgId", 0, winreg.REG_SZ, "roblox")
                winreg.CloseKey(uc_key)
            except Exception:
                pass

            try:
                import winreg
                chrome_pol = r"Software\Policies\Google\Chrome"
                pol_key = winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, chrome_pol,
                                              0, winreg.KEY_SET_VALUE)
                winreg.SetValueEx(pol_key, "ExternalProtocolDialogShowAlwaysOpenCheckbox",
                                  0, winreg.REG_DWORD, 0)
                winreg.CloseKey(pol_key)
            except Exception:
                pass

            flags = [
                chrome,
                f"--user-data-dir={profile_dir}",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-sync",
                "--disable-background-networking",
                "--disable-client-side-phishing-detection",
                "--disable-session-crashed-bubble",
                "--disable-infobars",
                "--no-process-singleton",
                "--disable-external-protocol-dialog",
                "--protocol-handler-bypass-list=roblox",
                "--disable-features=ExternalProtocolDialog",
                private_server_url,
            ]
            try:
                if sys.platform == "win32":
                    DETACHED = 0x00000008
                    NEW_GRP  = 0x00000200
                    cf = DETACHED | NEW_GRP
                else:
                    cf = 0
                subprocess.Popen(
                    flags,
                    creationflags=cf,
                    close_fds=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                self.root.after(0, lambda: (
                    self._log_activity(
                        f"🚀 Chrome launched for {username} → {private_server_url[:55]}…"),
                    self._toast(f"🚀  {username} — joining server…"),
                ))

                def _watch_for_roblox_pid(uname=username):
                    import psutil as _psutil
                    deadline = time.time() + 60

                    known_before = set()
                    try:
                        for proc in _psutil.process_iter(["pid", "name"]):
                            try:
                                if proc.info["name"].lower() == "robloxplayerbeta.exe":
                                    known_before.add(proc.info["pid"])
                            except (_psutil.NoSuchProcess, _psutil.AccessDenied):
                                pass
                    except Exception:
                        pass

                    if self._detection_mgr:
                        for pid in self._detection_mgr.username_pid_map.values():
                            known_before.add(pid)

                    while time.time() < deadline:
                        time.sleep(2)
                        try:
                            for proc in _psutil.process_iter(["pid", "name"]):
                                try:
                                    if proc.info["name"].lower() == "robloxplayerbeta.exe":
                                        pid = proc.info["pid"]
                                        if pid not in known_before:
                                            if self._detection_mgr:
                                                self._detection_mgr.register_pid(uname, pid)
                                                self.root.after(0, lambda p=pid, u=uname:
                                                    self._log_activity(
                                                        f"🔍 Roblox PID {p} registered for {u}"))
                                            return
                                except (_psutil.NoSuchProcess, _psutil.AccessDenied):
                                    pass
                        except Exception:
                            pass

                if WIN32_AVAILABLE:
                    threading.Thread(target=_watch_for_roblox_pid, daemon=True).start()
            except Exception as ex:
                err = str(ex)
                self.root.after(0, lambda e=err: (
                    webbrowser.open(private_server_url),
                    self._toast(f"⚠️  Chrome failed: {e[:50]}"),
                    self._log_activity(f"⚠ Chrome launch error for {username}: {e}"),
                ))

        if threaded:
            threading.Thread(target=_do, daemon=True).start()
        else:
            _do()

    def _acct_refresh_list(self):
        try:
            for w in self._acct_list_frame.winfo_children():
                w.destroy()
            try:
                self._acct_count_badge.config(
                    text=f"  {len(self.accounts)} accounts  ")
            except Exception:
                pass
            if not self.accounts:
                empty = tk.Frame(self._acct_list_frame, bg=BG_BASE,
                                 bd=0, highlightthickness=0)
                empty.grid(row=0, column=0, sticky="ew", pady=(20, 0))
                empty.columnconfigure(0, weight=1)

                ic = tk.Canvas(empty, width=52, height=52, bg=BG_BASE,
                               highlightthickness=0)
                ic.create_oval(13, 1, 39, 27, fill=TEXT_FAINTEST, outline="")
                ic.create_arc(2, 28, 50, 64, start=0, extent=180,
                              fill=TEXT_FAINTEST, outline="")
                ic.grid(row=0, column=0, pady=(0, 8))

                lbl(empty, "No accounts added", fg=TEXT_DIM, bg=BG_BASE,
                    font=("Segoe UI", 10)).grid(row=1, column=0)
                return

            for idx, acct in enumerate(self.accounts):
                outer = tk.Frame(self._acct_list_frame, bg=BG_CARD, bd=0,
                                 highlightthickness=1, highlightbackground=BORDER)
                outer.grid(row=idx, column=0, sticky="ew", pady=3)
                outer.columnconfigure(0, weight=1)

                hdr = tk.Frame(outer, bg=BG_CARD, cursor="hand2")
                hdr.pack(fill="x")

                tk.Frame(hdr, bg=ACCENT, width=3, bd=0,
                         highlightthickness=0).pack(side="left", fill="y")

                arrow = make_arrow_canvas(hdr, bg=BG_CARD)
                arrow.pack(side="left", padx=(8, 0), pady=8)

                av_cv = tk.Canvas(hdr, width=32, height=32, bg=BG_CARD,
                                  highlightthickness=0)
                uname = acct.get("roblox_username", "")
                av_cv.create_oval(1, 1, 31, 31, fill=ACCENT_DIM, outline=ACCENT)
                av_cv.create_text(16, 16, text=uname[0].upper() if uname else "?",
                                  fill=TEXT_PRIMARY, font=("Segoe UI", 10, "bold"),
                                  tags="ph")
                av_cv.pack(side="left", padx=(8, 6))

                if uname:
                    threading.Thread(
                        target=self._load_avatar_into_canvas,
                        args=(uname, av_cv, 32), daemon=True).start()

                lbl(hdr, uname, fg=TEXT_PRIMARY, bg=BG_CARD,
                    font=("Segoe UI", 9, "bold")).pack(side="left")

                ps_preview = acct.get("private_server", "").strip()
                ps_short = (ps_preview[:40] + "...") if len(ps_preview) > 40 else ps_preview
                lbl(hdr, ps_short if ps_short else "No server set",
                    fg=ACCENT if ps_short else TEXT_FAINT,
                    bg=BG_CARD, font=("Segoe UI", 7)).pack(
                        side="left", padx=(10, 0))

                has_cookie = bool(acct.get("roblosecurity", "").strip())
                tk.Label(hdr,
                         text="🔑 Cookie" if has_cookie else "No Cookie",
                         fg="#22c55e" if has_cookie else TEXT_FAINT,
                         bg=BG_CARD, font=("Segoe UI", 7, "bold"),
                         padx=6).pack(side="right", padx=(0, 8))

                body = tk.Frame(outer, bg=BG_ITEM, bd=0,
                                highlightthickness=1,
                                highlightbackground=BORDER_ITEM)
                expanded = [False]
                _animating = [False]
                _last_toggle = [0.0]

                def _toggle(e=None, _body=body, _arrow=arrow, _exp=expanded,
                            _lt=_last_toggle, _outer=outer, _anim=_animating):
                    import time as _time
                    now = _time.monotonic()
                    if now - _lt[0] < 0.35:
                        return "break"
                    _lt[0] = now
                    if _exp[0]:
                        _body.pack_forget()
                        _anim_arrow(_arrow, expanding=False)
                        _anim_border(_outer, ACCENT, BORDER, steps=8, delay=10)
                        _exp[0] = False
                    else:
                        _anim[0] = True
                        _body.pack(fill="x", padx=8, pady=(0, 8))
                        _anim_arrow(_arrow, expanding=True)
                        _anim_border(_outer, BORDER, ACCENT, steps=8, delay=10)
                        _exp[0] = True
                        if _ANIM_ROOT:
                            _ANIM_ROOT.after(120, lambda: _anim.__setitem__(0, False))
                    return "break"

                def _hdr_enter(e, _h=hdr, _o=outer):
                    _anim_bg(_h, BG_CARD, BG_HOVER, steps=6, delay=7)
                    _anim_border(_o, BORDER, "#3a3f5c", steps=6, delay=7)
                def _hdr_leave(e, _h=hdr, _o=outer, _exp=expanded):
                    _anim_bg(_h, BG_HOVER, BG_CARD, steps=6, delay=7)
                    target_border = ACCENT if _exp[0] else BORDER
                    _anim_border(_o, "#3a3f5c", target_border, steps=6, delay=7)

                hdr.bind("<Button-1>", _toggle)
                hdr.bind("<Enter>", _hdr_enter)
                hdr.bind("<Leave>", _hdr_leave)
                for _child in [arrow, av_cv]:
                    _child.bind("<Button-1>", _toggle)
                    _child.bind("<Enter>", _hdr_enter)
                    _child.bind("<Leave>", _hdr_leave)

                EDIT_BG = "#0d1120"
                EDIT_BD = "#2a2f4a"
                body.columnconfigure(0, weight=1)

                tk.Label(body, text="Roblox Username", fg="#8892b0", bg=BG_ITEM,
                         font=("Segoe UI", 8, "bold"), anchor="w").pack(
                             anchor="w", padx=12, pady=(10, 2))
                name_var = tk.StringVar(value=acct.get("roblox_username", ""))
                name_e = tk.Entry(body, textvariable=name_var,
                                  bg=EDIT_BG, fg=TEXT_MUTED,
                                  insertbackground=ACCENT, relief="flat",
                                  font=("Segoe UI", 9),
                                  highlightthickness=1, highlightbackground=EDIT_BD,
                                  highlightcolor=ACCENT)
                name_e.pack(fill="x", padx=12, ipady=6, pady=(0, 8))

                tk.Label(body, text="Private Server URL", fg="#8892b0", bg=BG_ITEM,
                         font=("Segoe UI", 8, "bold"), anchor="w").pack(
                             anchor="w", padx=12, pady=(0, 2))
                ps_var = tk.StringVar(value=acct.get("private_server", ""))
                ps_e = tk.Entry(body, textvariable=ps_var,
                                bg=EDIT_BG, fg=TEXT_MUTED,
                                insertbackground=ACCENT, relief="flat",
                                font=("Segoe UI", 9),
                                highlightthickness=1, highlightbackground=EDIT_BD,
                                highlightcolor=ACCENT)
                ps_e.pack(fill="x", padx=12, ipady=6, pady=(0, 4))

                has_cookie = bool(acct.get("roblosecurity", "").strip())
                ck_row = tk.Frame(body, bg=BG_ITEM)
                ck_row.pack(fill="x", padx=12, pady=(0, 10))
                tk.Label(ck_row, text=".ROBLOSECURITY:",
                         fg=TEXT_FAINT, bg=BG_ITEM,
                         font=("Segoe UI", 7)).pack(side="left")
                tk.Label(ck_row,
                         text="✓ Cookie saved" if has_cookie else "⚠ No cookie — will open in browser",
                         fg="#22c55e" if has_cookie else WARN,
                         bg=BG_ITEM, font=("Segoe UI", 7, "bold")).pack(side="left", padx=(6, 0))

                btn_r = tk.Frame(body, bg=BG_ITEM)
                btn_r.pack(fill="x", padx=12, pady=(0, 10))

                def _save_acct(_idx=idx, _acct=acct, _nv=name_var, _pv=ps_var,
                               _arrow=arrow, _outer=outer):
                    new_name = _nv.get().strip()
                    new_ps   = _pv.get().strip()
                    if not new_name:
                        self._toast("⚠  Username is required")
                        return
                    if not new_ps or not new_ps.startswith("http"):
                        self._toast("⚠  Private Server URL is required")
                        return
                    _acct["roblox_username"] = new_name
                    _acct["private_server"]  = new_ps
                    self._save_config()
                    self._acct_refresh_list()
                    self._toast(f"✓  Account '{new_name}' saved")

                def _launch_acct(_pv=ps_var, _acct=acct, _uname=uname):
                    url    = _pv.get().strip()
                    cookie = _acct.get("roblosecurity", "").strip()
                    if not url.startswith("http"):
                        self._toast("⚠  No valid server URL")
                        return
                    self._hold_singleton_mutex()
                    self._launch_account_with_cookie(_uname, url, cookie)

                def _join_ps(_pv=ps_var):
                    url = _pv.get().strip()
                    if url.startswith("http"):
                        webbrowser.open(url)
                    else:
                        self._toast("⚠  No valid server URL")

                accent_btn(btn_r, "💾  Save", command=_save_acct,
                           padx=10, pady=4).pack(side="left", padx=(0, 6))

                launch_b = tk.Button(btn_r, text="🚀 Launch",
                         fg="#ffffff", bg="#22c55e",
                         font=("Segoe UI", 9, "bold"),
                         relief="flat", bd=0, cursor="hand2",
                         activebackground="#16a34a", activeforeground="#ffffff",
                         command=_launch_acct, padx=8, pady=4)
                launch_b.pack(side="left", padx=(0, 6))
                launch_b.bind("<Enter>",         lambda e, b=launch_b: _anim_bg(b, "#22c55e", "#16a34a", steps=6, delay=8))
                launch_b.bind("<Leave>",         lambda e, b=launch_b: _anim_bg(b, "#16a34a", "#22c55e", steps=6, delay=8))
                launch_b.bind("<ButtonPress-1>", lambda e, b=launch_b: _anim_bg(b, "#16a34a", "#0f7a36", steps=3, delay=5))
                launch_b.bind("<ButtonRelease-1>", lambda e, b=launch_b: _anim_bg(b, "#0f7a36", "#16a34a", steps=3, delay=5))

                icon_btn(btn_r, "🔗 Join", fg=ACCENT, bg=ACCENT_DIM,
                         hover_fg=TEXT_PRIMARY, hover_bg=ACCENT,
                         padx=8, pady=4,
                         command=_join_ps).pack(side="left", padx=(0, 6))

                red_btn(btn_r, "✕ Remove", padx=8, pady=4,
                        command=lambda i=idx: self._acct_remove(i)).pack(side="left")
        except Exception as ex:
            print("acct_refresh error:", ex)


    def _page_webhooks(self, parent):
        page = fr(parent, bg=BG_BASE)
        page.columnconfigure(0, weight=1)
        page.rowconfigure(3, weight=1)

        lbl(page, "Webhooks", fg=TEXT_PRIMARY, bg=BG_BASE,
            font=("Segoe UI", 15, "bold")).grid(
                row=0, column=0, sticky="w", padx=20, pady=(16, 0))

        sub = fr(page, bg=BG_BASE)
        sub.grid(row=1, column=0, sticky="ew", padx=20, pady=(10, 0))
        sub.columnconfigure(1, weight=1)

        lbl(sub, "Webhook Manager", fg=TEXT_PRIMARY, bg=BG_BASE,
            font=("Segoe UI", 11, "bold")).pack(side="left")

        self._wh_count_badge = tk.Label(
            sub, text=f"  {len(self.webhooks)} webhook{'s' if len(self.webhooks) != 1 else ''}  ",
            fg="#a0a8c0", bg="#1e2236",
            font=("Segoe UI", 8), padx=6, pady=2,
            relief="flat", bd=0)
        self._wh_count_badge.pack(side="left", padx=10)

        add_btn = accent_btn(
            sub, "＋  Add Webhook",
            command=self._wh_toggle_form,
            padx=14, pady=6)
        add_btn.pack(side="right")

        lbl(page,
            "Configure Discord webhooks and choose which accounts trigger them.",
            fg="#6b7494", bg=BG_BASE,
            font=("Segoe UI", 9)).grid(
                row=2, column=0, sticky="w", padx=20, pady=(6, 10))

        sf = ScrollFrame(page, bg=BG_BASE)
        sf.grid(row=3, column=0, sticky="nsew", padx=14, pady=(0, 8))
        self._wh_sf    = sf
        self._wh_inner = sf.inner
        self._wh_inner.columnconfigure(0, weight=1)

        FORM_BG     = "#13172a"
        FORM_BORDER = "#4a4dcc"
        ENTRY_BG    = "#0d1120"
        ENTRY_BD    = "#2a2f4a"

        form_outer = tk.Frame(self._wh_inner, bg=FORM_BG, bd=0,
                              highlightthickness=1,
                              highlightbackground=FORM_BORDER)
        form_outer.columnconfigure(0, weight=1)
        self._wh_form_card = form_outer
        self._wh_form_visible = False

        lbl(form_outer, "Add New Webhook", fg=TEXT_PRIMARY, bg=FORM_BG,
            font=("Segoe UI", 10, "bold")).grid(
                row=0, column=0, sticky="w", padx=18, pady=(16, 8))

        fields_frame = tk.Frame(form_outer, bg=FORM_BG)
        fields_frame.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 8))
        fields_frame.columnconfigure(0, weight=1)

        tk.Label(fields_frame, text="Webhook Name",
                 fg="#8892b0", bg=FORM_BG,
                 font=("Segoe UI", 8, "bold"),
                 anchor="w").pack(anchor="w", pady=(0, 4))
        self._wh_name_var = tk.StringVar()
        name_ent = tk.Entry(fields_frame, textvariable=self._wh_name_var,
                            bg=ENTRY_BG, fg="#5a6280",
                            insertbackground=TEXT_PRIMARY,
                            relief="flat", font=("Segoe UI", 9),
                            highlightthickness=1,
                            highlightbackground=ENTRY_BD,
                            highlightcolor="#5c5fe8")
        name_ent.insert(0, "e.g. My Server")
        name_ent.pack(fill="x", ipady=7, pady=(0, 10))
        def _nf_in(e):
            if name_ent.get() == "e.g. My Server":
                name_ent.delete(0, "end")
                name_ent.config(fg=TEXT_MUTED)
        def _nf_out(e):
            if not name_ent.get().strip():
                name_ent.insert(0, "e.g. My Server")
                name_ent.config(fg="#5a6280")
        name_ent.bind("<FocusIn>", _nf_in)
        name_ent.bind("<FocusOut>", _nf_out)

        tk.Label(fields_frame, text="Webhook URL",
                 fg="#8892b0", bg=FORM_BG,
                 font=("Segoe UI", 8, "bold"),
                 anchor="w").pack(anchor="w", pady=(0, 4))
        self._wh_url_var = tk.StringVar()
        url_ent = tk.Entry(fields_frame, textvariable=self._wh_url_var,
                           bg=ENTRY_BG, fg="#5a6280",
                           insertbackground=TEXT_PRIMARY,
                           relief="flat", font=("Segoe UI", 9),
                           highlightthickness=1,
                           highlightbackground=ENTRY_BD,
                           highlightcolor="#5c5fe8")
        url_ent.insert(0, "https://discord.com/api/webhooks/...")
        url_ent.pack(fill="x", ipady=7, pady=(0, 10))
        def _uf_in(e):
            if url_ent.get() == "https://discord.com/api/webhooks/...":
                url_ent.delete(0, "end")
                url_ent.config(fg=TEXT_MUTED)
        def _uf_out(e):
            if not url_ent.get().strip():
                url_ent.insert(0, "https://discord.com/api/webhooks/...")
                url_ent.config(fg="#5a6280")
        url_ent.bind("<FocusIn>", _uf_in)
        url_ent.bind("<FocusOut>", _uf_out)

        tk.Label(fields_frame, text="Target Accounts",
                 fg="#8892b0", bg=FORM_BG,
                 font=("Segoe UI", 8, "bold"),
                 anchor="w").pack(anchor="w", pady=(0, 6))

        targets_card = tk.Frame(fields_frame, bg=BG_CARD, bd=0,
                                highlightthickness=1, highlightbackground=BORDER)
        targets_card.pack(fill="x", pady=(0, 6))

        self._wh_target_vars = {}
        self._wh_all_var     = tk.BooleanVar(value=False)

        def _rebuild_target_checkboxes():
            for w in targets_card.winfo_children():
                w.destroy()
            self._wh_target_vars.clear()

            all_row = tk.Frame(targets_card, bg=BG_CARD)
            all_row.pack(fill="x", padx=12, pady=(8, 4))
            all_cb = styled_check(all_row, variable=self._wh_all_var,
                                  bg=BG_CARD, selectcolor=ACCENT,
                                  command=_on_all_toggle)
            all_cb.pack(side="left")
            tk.Label(all_row, text="All Accounts",
                     fg=TEXT_PRIMARY, bg=BG_CARD,
                     font=("Segoe UI", 9, "bold")).pack(side="left", padx=(6, 0))
            tk.Label(all_row, text="(Send to all detected accounts)",
                     fg=TEXT_FAINT, bg=BG_CARD,
                     font=("Segoe UI", 8)).pack(side="left", padx=(8, 0))

            tk.Frame(targets_card, bg=BORDER, height=1).pack(fill="x", padx=8)

            if not self.accounts:
                tk.Label(targets_card, text="No accounts added yet — go to Accounts tab first.",
                         fg=TEXT_FAINT, bg=BG_CARD,
                         font=("Segoe UI", 8)).pack(padx=12, pady=8, anchor="w")
                return

            for acct in self.accounts:
                uname = acct.get("roblox_username", "")
                var = tk.BooleanVar(value=False)
                self._wh_target_vars[uname] = var

                row = tk.Frame(targets_card, bg=BG_CARD)
                row.pack(fill="x", padx=12, pady=3)

                cb = styled_check(row, variable=var,
                                  bg=BG_CARD, selectcolor=ACCENT)
                cb.pack(side="left")

                is_active = False
                if self._detection_mgr:
                    is_active = bool(self._detection_mgr._get_log_for_user(uname))
                status_cv = tk.Canvas(row, width=8, height=8, bg=BG_CARD,
                                      highlightthickness=0)
                status_cv.create_oval(1, 1, 7, 7,
                                      fill="#22c55e" if is_active else RED_BG,
                                      outline="#22c55e" if is_active else RED)
                status_cv.pack(side="left", padx=(6, 2))

                av = tk.Canvas(row, width=22, height=22, bg=BG_CARD,
                               highlightthickness=0, bd=0)
                av.create_oval(2, 2, 20, 20, fill=ACCENT_DIM, outline=ACCENT)
                av.create_text(11, 11, text=uname[0].upper() if uname else "?",
                               fill=TEXT_PRIMARY, font=("Segoe UI", 8, "bold"))
                av.pack(side="left", padx=(2, 8))

                tk.Label(row, text=uname,
                         fg=TEXT_PRIMARY, bg=BG_CARD,
                         font=("Segoe UI", 9)).pack(side="left")
                status_txt = "● active" if is_active else "○ offline"
                tk.Label(row, text=f"  {status_txt}",
                         fg="#22c55e" if is_active else TEXT_FAINT,
                         bg=BG_CARD, font=("Segoe UI", 7)).pack(side="left")

            targets_card.pack(fill="x", pady=(0, 6))

        def _on_all_toggle():
            if self._wh_all_var.get():
                for v in self._wh_target_vars.values():
                    v.set(False)

        _rebuild_target_checkboxes()
        self._rebuild_wh_targets = _rebuild_target_checkboxes

        btn_row = tk.Frame(form_outer, bg=FORM_BG)
        btn_row.grid(row=2, column=0, sticky="e", padx=18, pady=(6, 16))

        cancel_b = icon_btn(
            btn_row, "Cancel",
            fg=TEXT_MUTED, bg=BG_ITEM,
            hover_fg=RED, hover_bg=RED_BG,
            font=("Segoe UI", 9),
            command=self._wh_hide_form, padx=14, pady=6)
        cancel_b.pack(side="left", padx=(0, 10))

        confirm_b = accent_btn(
            btn_row, "✓  Save Webhook",
            command=lambda *_: self._wh_confirm(name_ent, url_ent),
            padx=14, pady=6)
        confirm_b.pack(side="left")

        self._wh_list_frame = fr(self._wh_inner, bg=BG_BASE)
        self._wh_list_frame.grid(row=1, column=0, sticky="ew")
        self._wh_list_frame.columnconfigure(0, weight=1)
        self._wh_refresh_list()
        return page

    def _wh_toggle_form(self):
        if self._wh_form_visible:
            self._wh_hide_form()
        else:
            self._wh_show_form()

    def _wh_show_form(self):
        try:
            self._wh_form_card.grid(row=0, column=0, sticky="ew", pady=(0, 12))
            self._wh_form_visible = True
            if callable(getattr(self, "_rebuild_wh_targets", None)):
                self._rebuild_wh_targets()
        except Exception:
            pass

    def _wh_hide_form(self):
        try:
            self._wh_form_card.grid_remove()
            self._wh_form_visible = False
        except Exception:
            pass

    def _wh_confirm(self, name_ent, url_ent):
        name = name_ent.get().strip()
        url  = url_ent.get().strip()
        if not name or name == "e.g. My Server":
            name_ent.config(highlightbackground=RED)
            return
        if not url or url == "https://discord.com/api/webhooks/..." or not url.startswith("http"):
            url_ent.config(highlightbackground=RED)
            return
        name_ent.config(highlightbackground=BORDER_ITEM)
        url_ent.config(highlightbackground=BORDER_ITEM)

        if self._wh_all_var.get():
            targets = ["all"]
        else:
            targets = [u for u, v in self._wh_target_vars.items() if v.get()]
            if not targets:
                targets = ["all"]

        self.webhooks.append({"name": name, "url": url, "targets": targets})
        self._wh_hide_form()
        self._wh_refresh_list()
        self._save_config()
        self._toast(f"✓  Webhook '{name}' added")

    def _wh_remove(self, idx):
        if 0 <= idx < len(self.webhooks):
            name = self.webhooks.pop(idx)["name"]
            self._wh_refresh_list()
            self._save_config()
            self._toast(f"✕  Removed '{name}'")

    def _wh_refresh_chips(self):
        """
        Lightweight update — only refreshes the active-accounts chip text
        on existing webhook cards. Does NOT rebuild cards, so expanded state
        is preserved.
        """
        if not hasattr(self, "_wh_chip_labels"):
            return
        for idx, (wh, chip_lbl) in list(self._wh_chip_labels.items()):
            try:
                targets = wh.get("targets", ["all"])
                if "all" in targets:
                    active_count = 0
                    if self._detection_mgr:
                        for acct in self.accounts:
                            uname = acct.get("roblox_username", "").strip()
                            if uname and self._detection_mgr._get_log_for_user(uname):
                                active_count += 1
                    chip_text = (f"All Accounts  ({active_count} active)"
                                 if active_count > 0 else "All Accounts")
                else:
                    active_t   = [t for t in targets if self._detection_mgr and
                                  self._detection_mgr._get_log_for_user(t)]
                    inactive_t = [t for t in targets if t not in active_t]
                    if active_t:
                        chip_text = "🟢 " + ", ".join(active_t)
                        if inactive_t:
                            chip_text += f"  🔴 {len(inactive_t)} offline"
                    else:
                        chip_text = "⚫ " + ", ".join(targets) + " (none active)"
                chip_lbl.config(text=f"→ {chip_text}")
            except Exception:
                pass

    def _wh_refresh_list(self):
        self._wh_chip_labels = {}
        try:
            for w in self._wh_list_frame.winfo_children():
                w.destroy()
            try:
                n = len(self.webhooks)
                self._wh_count_badge.config(
                    text=f"  {n} webhook{'s' if n != 1 else ''}  ")
            except Exception:
                pass

            if not self.webhooks:
                empty = tk.Frame(self._wh_list_frame, bg=BG_BASE,
                                 bd=0, highlightthickness=0)
                empty.grid(row=0, column=0, sticky="ew", pady=(20, 0))
                empty.columnconfigure(0, weight=1)
                lbl(empty, "No webhooks configured yet.", fg=TEXT_DIM, bg=BG_BASE,
                    font=("Segoe UI", 10)).grid(row=0, column=0)
                return

            for idx, wh in enumerate(self.webhooks):
                outer = tk.Frame(self._wh_list_frame, bg=BG_CARD, bd=0,
                                 highlightthickness=1, highlightbackground=BORDER)
                outer.grid(row=idx, column=0, sticky="ew", pady=3)
                outer.columnconfigure(0, weight=1)

                hdr = tk.Frame(outer, bg=BG_CARD, cursor="hand2")
                hdr.pack(fill="x")
                hdr.columnconfigure(1, weight=1)

                tk.Frame(hdr, bg=ACCENT, width=3, bd=0,
                         highlightthickness=0).grid(row=0, column=0,
                                                    rowspan=2, sticky="ns")

                arrow = make_arrow_canvas(hdr, bg=BG_CARD)
                arrow.grid(row=0, column=1, sticky="w", padx=(8, 0), pady=(8, 8))

                lbl(hdr, wh["name"], fg=TEXT_PRIMARY, bg=BG_CARD,
                    font=("Segoe UI", 9, "bold")).grid(
                        row=0, column=2, sticky="w", padx=8, pady=(8, 8))

                targets = wh.get("targets", ["all"])
                if "all" in targets:
                    active_count = 0
                    if self._detection_mgr:
                        for acct in self.accounts:
                            uname = acct.get("roblox_username", "").strip()
                            if uname and self._detection_mgr._get_log_for_user(uname):
                                active_count += 1
                    if active_count > 0:
                        chip_text = f"All Accounts  ({active_count} active)"
                    else:
                        chip_text = "All Accounts"
                else:
                    active_targets = []
                    inactive_targets = []
                    for t in targets:
                        is_active = False
                        if self._detection_mgr:
                            is_active = bool(self._detection_mgr._get_log_for_user(t))
                        if is_active:
                            active_targets.append(t)
                        else:
                            inactive_targets.append(t)
                    if active_targets:
                        chip_text = "🟢 " + ", ".join(active_targets)
                        if inactive_targets:
                            chip_text += f"  🔴 {len(inactive_targets)} offline"
                    else:
                        chip_text = "⚫ " + ", ".join(targets) + " (none active)"
                _chip_lbl = lbl(hdr, f"→ {chip_text}", fg=ACCENT, bg=BG_CARD,
                    font=("Segoe UI", 7))
                _chip_lbl.grid(row=0, column=3, sticky="w", padx=(0, 12), pady=(8, 8))
                if not hasattr(self, "_wh_chip_labels"):
                    self._wh_chip_labels = {}
                self._wh_chip_labels[idx] = (wh, _chip_lbl)

                body = tk.Frame(outer, bg=BG_ITEM, bd=0,
                                highlightthickness=1, highlightbackground=BORDER_ITEM)
                expanded   = [False]
                _animating = [False]
                _fired     = [False]

                def _toggle(e=None,
                            _b=body, _ar=arrow, _ex=expanded,
                            _ou=outer, _an=_animating, _fi=_fired):
                    if _fi[0]:
                        return "break"
                    _fi[0] = True
                    _ou.after(0, lambda: _fi.__setitem__(0, False))
                    if _ex[0]:
                        _b.pack_forget()
                        _anim_arrow(_ar, expanding=False)
                        _anim_border(_ou, ACCENT, BORDER, steps=8, delay=10)
                        _ex[0] = False
                    else:
                        _an[0] = True
                        _b.pack(fill="x", padx=8, pady=(0, 8))
                        _anim_arrow(_ar, expanding=True)
                        _anim_border(_ou, BORDER, ACCENT, steps=8, delay=10)
                        _ex[0] = True
                        _ou.after(120, lambda: _an.__setitem__(0, False))
                    return "break"

                def _whdr_enter(e, _h=hdr, _o=outer):
                    _anim_bg(_h, BG_CARD, BG_HOVER, steps=6, delay=7)
                    _anim_border(_o, BORDER, "#3a3f5c", steps=6, delay=7)
                def _whdr_leave(e, _h=hdr, _o=outer, _ex=expanded):
                    _anim_bg(_h, BG_HOVER, BG_CARD, steps=6, delay=7)
                    target_border = ACCENT if _ex[0] else BORDER
                    _anim_border(_o, "#3a3f5c", target_border, steps=6, delay=7)

                for _w in [hdr, arrow] + list(hdr.winfo_children()):
                    _w.bind("<Button-1>", _toggle)
                    _w.bind("<Enter>",    _whdr_enter)
                    _w.bind("<Leave>",    _whdr_leave)

                EDIT_BG  = "#0d1120"
                EDIT_BD  = "#2a2f4a"

                body.columnconfigure(0, weight=1)

                tk.Label(body, text="Webhook Name", fg="#8892b0", bg=BG_ITEM,
                         font=("Segoe UI", 8, "bold"), anchor="w").pack(
                             anchor="w", padx=12, pady=(10, 2))
                name_var = tk.StringVar(value=wh.get("name", ""))
                name_e = tk.Entry(body, textvariable=name_var,
                                  bg=EDIT_BG, fg=TEXT_MUTED,
                                  insertbackground=ACCENT, relief="flat",
                                  font=("Segoe UI", 9),
                                  highlightthickness=1, highlightbackground=EDIT_BD,
                                  highlightcolor=ACCENT)
                name_e.pack(fill="x", padx=12, ipady=6, pady=(0, 8))

                tk.Label(body, text="Webhook URL", fg="#8892b0", bg=BG_ITEM,
                         font=("Segoe UI", 8, "bold"), anchor="w").pack(
                             anchor="w", padx=12, pady=(0, 2))
                url_var = tk.StringVar(value=wh.get("url", ""))
                url_e = tk.Entry(body, textvariable=url_var,
                                 bg=EDIT_BG, fg=TEXT_MUTED,
                                 insertbackground=ACCENT, relief="flat",
                                 font=("Segoe UI", 9),
                                 highlightthickness=1, highlightbackground=EDIT_BD,
                                 highlightcolor=ACCENT)
                url_e.pack(fill="x", padx=12, ipady=6, pady=(0, 8))

                tk.Label(body, text="Target Accounts", fg="#8892b0", bg=BG_ITEM,
                         font=("Segoe UI", 8, "bold"), anchor="w").pack(
                             anchor="w", padx=12, pady=(0, 4))

                cb_frame = tk.Frame(body, bg=BG_ITEM)
                cb_frame.pack(fill="x", padx=12, pady=(0, 8))

                cur_targets = wh.get("targets", ["all"])
                all_var  = tk.BooleanVar(value="all" in cur_targets)
                acct_vars = {}

                all_row = tk.Frame(cb_frame, bg=BG_ITEM)
                all_row.pack(fill="x", pady=2)
                styled_check(all_row, variable=all_var,
                             bg=BG_ITEM, selectcolor=ACCENT).pack(side="left")
                tk.Label(all_row, text="All Accounts",
                         fg=TEXT_PRIMARY, bg=BG_ITEM,
                         font=("Segoe UI", 9, "bold")).pack(side="left", padx=(4, 0))

                for acct in self.accounts:
                    uname = acct.get("roblox_username", "")
                    av = tk.BooleanVar(value=(uname in cur_targets))
                    acct_vars[uname] = av
                    ar = tk.Frame(cb_frame, bg=BG_ITEM)
                    ar.pack(fill="x", pady=2)
                    styled_check(ar, variable=av,
                                 bg=BG_ITEM, selectcolor=ACCENT).pack(side="left")
                    is_active = False
                    if self._detection_mgr:
                        is_active = bool(self._detection_mgr._get_log_for_user(uname))
                    status_cv = tk.Canvas(ar, width=8, height=8, bg=BG_ITEM,
                                         highlightthickness=0)
                    status_cv.create_oval(1, 1, 7, 7,
                                         fill="#22c55e" if is_active else RED_BG,
                                         outline="#22c55e" if is_active else RED)
                    status_cv.pack(side="left", padx=(4, 2))
                    dot_cv = tk.Canvas(ar, width=16, height=16, bg=BG_ITEM,
                                       highlightthickness=0)
                    dot_cv.create_oval(1,1,15,15, fill=ACCENT_DIM, outline=ACCENT)
                    dot_cv.create_text(8,8, text=uname[0].upper() if uname else "?",
                                       fill=TEXT_PRIMARY, font=("Segoe UI", 7, "bold"))
                    dot_cv.pack(side="left", padx=(2, 6))
                    status_txt = "● active" if is_active else "○ offline"
                    status_color = "#22c55e" if is_active else TEXT_FAINT
                    tk.Label(ar, text=uname, fg=TEXT_PRIMARY, bg=BG_ITEM,
                             font=("Segoe UI", 9)).pack(side="left")
                    tk.Label(ar, text=f"  {status_txt}", fg=status_color, bg=BG_ITEM,
                             font=("Segoe UI", 7)).pack(side="left")

                btn_row2 = tk.Frame(body, bg=BG_ITEM)
                btn_row2.pack(fill="x", padx=12, pady=(0, 10))

                def _save_edit(_idx=idx, _wh=wh, _nv=name_var, _uv=url_var,
                               _av=all_var, _cvs=acct_vars, _arrow=arrow):
                    new_name = _nv.get().strip()
                    new_url  = _uv.get().strip()
                    if not new_name or not new_url:
                        self._toast("⚠  Name and URL are required")
                        return
                    if _av.get():
                        new_targets = ["all"]
                    else:
                        new_targets = [u for u, v in _cvs.items() if v.get()]
                        if not new_targets:
                            new_targets = ["all"]
                    _wh["name"]    = new_name
                    _wh["url"]     = new_url
                    _wh["targets"] = new_targets
                    _arrow.config(text=new_name)
                    self._save_config()
                    self._wh_refresh_list()
                    self._toast(f"✓  Webhook '{new_name}' saved")

                accent_btn(btn_row2, "💾  Save", command=_save_edit,
                           padx=10, pady=4).pack(side="left", padx=(0, 6))

                icon_btn(btn_row2, "⚡ Test", fg=ACCENT, bg=ACCENT_DIM,
                         hover_fg=TEXT_PRIMARY, hover_bg=ACCENT,
                         padx=8, pady=4,
                         command=lambda w=wh: self._wh_send_test(w)).pack(
                             side="left", padx=(0, 6))

                red_btn(btn_row2, "✕ Remove", padx=8, pady=4,
                        command=lambda i=idx: self._wh_remove(i)).pack(side="left")
        except Exception as ex:
            print("wh_refresh error:", ex)

    def _wh_send_test(self, wh):
        url = wh.get("url", "").strip()
        if not url:
            self._toast("⚠  No webhook URL")
            return
        payload = {"embeds": [{
            "title": "⚡ Test — MultiFInstance",
            "description": f"Webhook **{wh['name']}** is working correctly.",
            "color": 0x5865f2,
            "footer": {"text": f"MultiFInstance v{VERSION}"},
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }]}
        threading.Thread(target=self._post_webhook, args=(url, payload), daemon=True).start()
        self._toast(f"⚡  Testing '{wh['name']}'…")


    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    import traceback
    _log = os.path.join(os.path.dirname(os.path.abspath(__file__)), "error_log.txt")
    try:
        if not _show_agreement_dialog():
            sys.exit(0)
        MultiFInstanceApp().run()
    except Exception:
        with open(_log, "w", encoding="utf-8") as _f:
            traceback.print_exc(file=_f)
        try:
            import tkinter.messagebox as _mb
            _mb.showerror("Crash", f"App crashed. See error_log.txt for details:\n\n{traceback.format_exc()[-800:]}")
        except Exception:
            pass
        raise
