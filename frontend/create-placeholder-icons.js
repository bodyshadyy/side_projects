// Script to create minimal placeholder PNG icons
// Creates valid PNG files that Chrome can load

const fs = require('fs')
const path = require('path')

// Minimal valid PNG file (1x1 pixel, transparent)
// This is a base64-encoded minimal PNG that Chrome will accept
const minimalPNG = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==',
  'base64'
)

const distDir = path.join(__dirname, 'dist')

// Ensure dist directory exists
if (!fs.existsSync(distDir)) {
  fs.mkdirSync(distDir, { recursive: true })
}

console.log('Creating placeholder PNG icons...')

// Create minimal placeholder PNGs for all required sizes
const sizes = [16, 48, 128]
sizes.forEach(size => {
  const iconPath = path.join(distDir, `icon${size}.png`)
  
  // Create a minimal valid PNG (Chrome will scale it)
  // This is a 1x1 transparent PNG - not ideal but will work
  fs.writeFileSync(iconPath, minimalPNG)
  console.log(`✓ Created icon${size}.png (minimal placeholder)`)
})

console.log('\n✓ Placeholder icons created!')
console.log('Note: These are minimal placeholders. For better appearance, replace with proper icons.')
console.log('You can use the icon-generator.html file to create better icons.')
