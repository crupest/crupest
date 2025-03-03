function createResetTimer(cleanup: () => void, timeout = 1) {
  let tag = 0
  return () => {
    clearTimeout(tag)
    tag = setTimeout(() => {
      cleanup()
    }, timeout * 1000)
  }
}

function createToast(duration: number = 1): (text: string) => void {
  const toast = document.createElement("div")
  toast.className = "toast"

  const reset = createResetTimer(() => {
      toast.remove()
  }, duration)

  return (text) => {
    if (!toast.isConnected) {
      document.body.appendChild(toast)
    }
    toast.textContent = text
    reset()
  }
}

const setToast = createToast()

const key = "force-color-scheme"
const dark = "dark"
const light = "light"
type Scheme = typeof dark | typeof light

const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)")

function fromMediaQuery(value: boolean | null): Scheme {
  if (value == null) { value = mediaQuery.matches}
  return value ? dark : light
}

function opposite(scheme: Scheme): Scheme {
  return scheme === dark ? light : dark
}

function updateScheme(theme: Scheme | null): Scheme {
  if (theme == null) { theme = fromMediaQuery(null) }
  document.querySelector("html")!.dataset["theme"] = theme
  return theme
}

mediaQuery.addEventListener("change", (e) => updateScheme(current || fromMediaQuery(e.matches)))

let current: Scheme | null = null

{
  const saved = localStorage.getItem(key)
  if ([null, dark, light].includes(saved)) {
    current = saved as never
  } else {
    console.log(`invalid saved theme: ${saved}`)
    localStorage.removeItem(key)
  }
}

updateScheme(current)

function saveScheme(value: Scheme | null) {
  current = value

  if (value == null) {
    localStorage.removeItem(key)
  } else {
    localStorage.setItem(key, value)
  }

  const real = updateScheme(value)
  setToast(`theme: ${current == null ? "system" : "force"}(${real})`)
}

function next(): Scheme | null {
  const sys = fromMediaQuery(null)
  if (current == null) {
    return opposite(sys)
  } else {
    if (current === sys) {
      return null;
    } else {
      return opposite(current)
    }
  }
}

window.addEventListener("load", () => {
  const slogon = document.getElementById("slogan")!
  let clicks: number = 0

  const reset = createResetTimer(() => {
    clicks = 0
  })

  slogon.addEventListener("click", () => {
    reset()
    clicks += 1
    if (clicks === 3) {
      saveScheme(next())
      clicks = 0
    }
  })
})
