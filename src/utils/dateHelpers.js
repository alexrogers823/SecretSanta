// EST is UTC-5 year-round for our purposes: both Nov 25 and Dec 25 always
// fall after US DST ends (first Sunday in November), so EST (not EDT)
// applies to both target dates every year.
const EST_OFFSET_HOURS = 5

const getNextOccurrenceUTC = (month, day, estHour) => {
  const now = Date.now()
  const year = new Date().getUTCFullYear()
  const buildUTC = y => Date.UTC(y, month, day, estHour + EST_OFFSET_HOURS, 0, 0)
  const targetUTC = buildUTC(year)
  return new Date(targetUTC <= now ? buildUTC(year + 1) : targetUTC)
}

// November 25th, 12:00pm EST (month is 0-indexed)
export const getNextMatchDate = () => getNextOccurrenceUTC(10, 25, 12)

// December 25th, 12:00am EST
export const getNextChristmasDate = () => getNextOccurrenceUTC(11, 25, 0)
