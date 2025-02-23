const key = "color-scheme"

type scheme = "dark" | "light" | null

function createResetTimer(cleanup: () => void, timeout = 1) {
  let tag = 0
  return () => {
    clearTimeout(tag)
    tag = setTimeout(() => {
      cleanup()
    }, timeout * 1000)
  }
}

let current = localStorage.getItem(key) as scheme

let inited = false

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

const themeToast = createToast()

function setTheme(value: scheme) {
  let message = ""
  current = value

  if (value == null) {
    const prefersDarkScheme = window.matchMedia("(prefers-color-scheme: dark)").matches
    value = prefersDarkScheme ? "dark" : "light"
    message = `theme: system(${value})`
    localStorage.removeItem(key)
  } else {
    message = `theme: force(${value})`
    localStorage.setItem(key, value)
  }

  document.body.dataset["theme"] = value

  if (inited) {
    themeToast(message)
  }
}

setTheme(current)
inited = true

function next(scheme: scheme): scheme {
  switch (scheme) {
    case "dark":
      return "light"
    case "light":
      return null
    default:
      return "dark"
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
      setTheme(next(current))
      clicks = 0
    }
  })
})

