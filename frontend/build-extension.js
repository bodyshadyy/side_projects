// Build script to prepare extension files
const fs = require('fs')
const path = require('path')

const distDir = path.join(__dirname, 'dist')
const rootDir = path.join(__dirname, '..')

// Copy manifest.json to dist
const manifestSrc = path.join(rootDir, 'manifest.json')
const manifestDest = path.join(distDir, 'manifest.json')
fs.copyFileSync(manifestSrc, manifestDest)
console.log('✓ Copied manifest.json')

// Copy background.js to dist
const backgroundSrc = path.join(rootDir, 'background.js')
const backgroundDest = path.join(distDir, 'background.js')
fs.copyFileSync(backgroundSrc, backgroundDest)
console.log('✓ Copied background.js')

// Check for icons and create placeholders if missing
const iconSizes = [16, 48, 128]
let missingIcons = []
iconSizes.forEach(size => {
  const iconPath = path.join(distDir, `icon${size}.png`)
  if (!fs.existsSync(iconPath)) {
    missingIcons.push(size)
  }
})

if (missingIcons.length > 0) {
  console.log(`\n⚠ Missing icon files: ${missingIcons.map(s => `icon${s}.png`).join(', ')}`)
  console.log('   Creating placeholder icons...')
  
  // Create minimal placeholder PNGs
  const minimalPNG = Buffer.from(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==',
    'base64'
  )
  
  missingIcons.forEach(size => {
    const iconPath = path.join(distDir, `icon${size}.png`)
    fs.writeFileSync(iconPath, minimalPNG)
    console.log(`   ✓ Created icon${size}.png (placeholder)`)
  })
  
  console.log('\n   Note: These are minimal placeholders. Replace with proper icons for better appearance.')
}

console.log('\n✓ Extension build complete!')
console.log('\nTo load the extension:')
console.log('1. Open Chrome and go to chrome://extensions/')
console.log('2. Enable "Developer mode"')
console.log('3. Click "Load unpacked"')
console.log('4. Select the "dist" folder')
