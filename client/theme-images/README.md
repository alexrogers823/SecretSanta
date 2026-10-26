# Theme images

These WebP files are what the site serves from the public `secret-santa-assets` bucket
(`https://storage.googleapis.com/secret-santa-assets/img/`). They were converted from the
original PNGs (in git history under `client/src/assets/`) at quality 85, keeping transparency.

Objects are cached for a year (`immutable`), so **never overwrite one**. To change an image,
give it a new name, upload it, then update the filename in the code:

```
gcloud storage cp theme-images/background-v2.webp gs://secret-santa-assets/img/ \
  --cache-control="public,max-age=31536000,immutable"
```
