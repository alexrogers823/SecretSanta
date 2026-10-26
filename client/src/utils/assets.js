// Theme images live in the public assets bucket rather than the JS bundle (plan step 2.10).
// They're cached for a year, so a changed image gets a new filename, e.g. background-v2.webp.
export const themeImageUrl = filename => `${process.env.REACT_APP_ASSETS_URL}/img/${filename}`
