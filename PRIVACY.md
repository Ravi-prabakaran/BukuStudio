# Privacy

BukuStudio often handles children's stories and drawings, so it is built to keep them with you.

**Stays on your computer**

- Your story, drawings, photos and every file BukuStudio makes are saved only in the `books/` folder in your working folder.
- The pages that open in your browser (choices, reading, drawings, pictures) run on your own computer at `127.0.0.1`. They aren't on the internet and other devices can't reach them.
- BukuStudio has no account, no analytics and no tracking.

**Goes to Claude**

- Your story, the text of your book and the pictures (including photos of drawings) are read by Claude to write the pages and draw or check the pictures, the same as anything you share in a Claude conversation. Your Claude plan's privacy terms apply.

**Goes to an image service, only if you add a key**

- If you add an OpenAI or Gemini key, the picture descriptions, character sheets and photos of drawings you chose to "color in" or "redraw" are sent to that service to make the pictures. Their privacy terms apply. Without a key, nothing is sent to an image service.

**Keys**

- Keys are read from a `.env` file you create. BukuStudio never displays, logs or sends them anywhere except to the service they belong to.

**Deleting**

- Delete a book's folder in `books/` to remove everything about it.
