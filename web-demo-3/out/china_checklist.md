# China access dependency checklist

| Third-party resource | Host | Replacement |
|---|---|---|
| Google Fonts | fonts.googleapis.com | self-host font files |
| Google Analytics / Tag Manager | googletagmanager.com | self-hosted analytics or regional analytics |
| Google Maps embed | maps.googleapis.com | static map image |
| reCAPTCHA | google.com/recaptcha | self-hosted captcha or server-side checks |
| YouTube embeds | youtube.com | self-hosted video file |
| Facebook pixel / SDK | connect.facebook.net | remove or load only outside China |
| X (Twitter) widgets | platform.twitter.com | plain text link-free share buttons |
| Instagram embeds | instagram.com | static images |
| Google-hosted libraries (jQuery etc.) | ajax.googleapis.com | self-host the library |
| Disqus comments | disqus.com | no third-party comments |

Generated pages scanned: 6; external references found: 0

Hosting: choose a host reachable from both regions (e.g. Hong Kong / Singapore region or ICP-filed mainland host plus overseas mirror); verify by real page loads from both sides.
