<!-- bump13 -->

# BeziAppBackend
A backend for BežiApp, an alternative and complete solution for Gimnazija Bežigrad students (and parents), written in FastAPI & Python.

# Functionalities
- [x] Integration with GimSIS - timetable, grades, gradings, absences, teachers etc.
- [x] Integration with Lo.Polis - fetch & change meals and checkouts
- [x] Examination (test) and note upload
- [x] School radio
- [x] Tarock counting software
- [x] OAUTH2 integration
- [x] BežiApp account system

# The problem
Gimnazija Bežigrad has made a very poorly written program as an alternative to [eAsistent](https://easistent.com), called GimSIS.
It's written in ASP.NET and not only it has a very outdated design, but also has many security loopholes, which haven't been addressed for years.

Gimnazija Bežigrad has also fallen into love with Microsoft and thus they've created every student a Microsoft account to access school computers
and to access the intranet, and boy, do they love to complicate...

GimSIS is the main application for timetables, gradings and grades, a so called SIS (Student Information System).
But while substitutions are a feature within GimSIS (as well as many other security loopholes :wink:), nobody uses them.

This leads to a massive confusion, and why exactly is it like that? Because Bežigrad publishes their substitution PDFs on intranet, instead of
importing them directly into GimSIS, which would've been a better solution.

Instead, us, the students, need to combine timetables by ourselves, which can be a hassle.

BUT, the story doesn't end here. If you thought it was bad, let's just add a cherry on top.

What does Gimnazija Bežigrad use for meal ordering and student ID cards? You guessed it right. It's not Bežigrad vulnerable software - it's even worse.
It's called [Lo.Polis](https://lopolis.si) and uses the most outdated design I've seen in my entire life.

In the end, they are paying Microsoft to use their poorly made services that always love to crash and are super buggy and laggy
(*cough* Teams, Office Online, Outlook *cough*), while everything (or most) could've been done in GimSIS,
paying Lo.Polis (too much) for meal ordering system, which could've easily been implemented into GimSIS...

I've simply had enough. Bežigrad needs an app that brings all of these services together into a one, simple to use app, and if the school isn't
going to provide us with the one, I'll do it myself.

So, that's the story of BežiApp.
