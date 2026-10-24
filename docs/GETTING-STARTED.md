# Make your first book with BukuStudio

BukuStudio turns a story into a real book you can sell on Amazon: a printed paperback (or hardcover for longer books) and a Kindle eBook. A child can tell the story and draw the pictures; Claude helps with the rest. You choose everything by tapping pictures.

You don't need any API keys or design skills. It takes about an hour for a picture book, most of it reading and choosing.

## What you need

- A computer (Mac, Windows or Linux) with **Python 3.10 or newer**.
- **Claude Code**, with a Claude plan that includes it.
- Optional: photos of the drawings you want in the book. Take them from straight above, in daylight.

## 1. Install BukuStudio (one time)

In Claude Code, type:

```
/plugin marketplace add Ravi-prabakaran/BukuStudio
/plugin install bukustudio@bukustudio
```

Then start a new Claude Code session in a folder where you'd like your books saved (for example a new folder called `My Books`).

## 2. Make a book

Type `/make-book`, or just say "I want to make a book". Then:

1. **Choose with pictures.** A page opens in your browser. Tap through the cards: who it's for, the size, the number of pages, the kind of pictures, and so on. Not sure? Tap "Pick for me". Kid mode shows one big card at a time and can read the choices aloud.
2. **Read your book.** Claude writes the pages from your story, keeping your names and favorite parts. A page opens where you pick a title and can change any words.
3. **Add your drawings** (if you said you have some). Upload a photo for any page, the cover or a character, and choose: keep it as it is, color it in, redraw it, or redraw it with simple shapes.
4. **Check the pictures.** You'll see the characters and the first two pictures. Keep them, or ask for another try with a note like "make Mia smaller". Then the rest are made the same way, and you check them all.
5. **Get your files.** BukuStudio makes everything Amazon needs and checks it against Amazon's rules.

Everything is saved in a `books/` folder inside your folder.

## 3. Publish on Amazon KDP

You do the upload yourself, at [kdp.amazon.com](https://kdp.amazon.com). Open your book's `listing.json` for every answer the form asks for.

| KDP asks for | Use this file |
|---|---|
| Title, description, keywords, categories, age range | `listing.json` |
| AI-generated content questions | `listing.json` → `ai_disclosure` |
| Paperback or hardcover manuscript | `print/interior.pdf` |
| Paperback or hardcover cover | `print/cover.pdf` |
| Kindle eBook manuscript | `print/kindle.epub` |
| Kindle eBook cover | `print/kindle-cover.jpg` |

Before you publish:

- **Order a printed proof copy** from KDP and look at it. Colors on paper differ from screens.
- For a **hardcover**, compare the cover size with KDP's cover calculator.
- Open `kindle.epub` in **Kindle Previewer** (free from Amazon) to see it on different devices.

## Pictures: Claude or an image service

With no setup, **Claude draws every picture itself**, in the style you chose. Simple shapes, cartoon, line art and colored pencil look best; watercolor and crayon are good; Claude's "3D" is simpler than real 3D art.

If you'd like painted pictures from an image service, you can add a key from OpenAI or Google Gemini. This is optional and costs a few dollars per book, paid to that service.

1. Make a file named `.env` in your books folder.
2. Put one line in it: `OPENAI_API_KEY=your-key` or `GEMINI_API_KEY=your-key`.
3. Keep this file private. Never share it or paste the key into a chat.

## Your family's privacy

See [PRIVACY.md](../PRIVACY.md). In short, everything stays on your computer unless you add an image service key.
