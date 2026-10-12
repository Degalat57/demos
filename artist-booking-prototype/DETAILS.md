# Artist booking interactive demo

Explore a fictional artist roster, compare performance packages, choose a date
and time, and create a simulated booking. Artist and admin views display the
same bookings; cancelling a booking makes its slot available again.
Booking dates use India local time. Profiles show typical performance times;
choose a date to see which times remain unbooked in this local demo.
For today's date, elapsed start times and the current minute are unavailable.

The first artist offers Basic (1 hour) for ₹25,000, Standard (2 hours) for
₹45,000 and Premium (full event) for ₹75,000. Typical performance starts are
10:00, 14:00, 18:00 and 20:00 in India local time, subject to date and booking
availability in this demo.

All artists, fees and payment activity are synthetic. A separate ₹500 platform
fee is added to the 20% artist advance. For a ₹25,000 package, the advance is
₹5,000, the simulated amount due now is ₹5,500, and the artist balance remains
₹20,000. Both the quote and booking receipt show these amounts separately.
This is a simulation: no money is charged and no real artist is reserved. Demo bookings
are stored only in this browser, with an in-memory fallback if browser storage
is unavailable. The Reset demo button asks before clearing local bookings.

Serve these static files over HTTP to use the browser's JavaScript module
support. The demo uses system fonts and CSS artwork without external images
or font services. It has no real payment processing, account system or booking
backend.

This is a functional prototype based on the supplied screen reference, not a full
14-screen implementation or a claim of pixel-perfect fidelity. Authentication
(OTP, Google and email sign-in), media galleries, chat and PDF messaging, backend
services and calendar integrations are outside this prototype. Payments, artist
availability and bookings are simulated locally; no real account is connected.
