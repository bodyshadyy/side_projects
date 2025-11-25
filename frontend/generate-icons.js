// Simple script to generate placeholder icons
// Note: This requires a package like 'canvas' or you can use online tools
// For now, this is a placeholder - you should create icons manually or use an online tool

const fs = require('fs')
const path = require('path')

console.log('Icon Generator')
console.log('==============')
console.log('\nTo create icons for the extension:')
console.log('1. Create a 128x128 pixel image with a tomato emoji or Pomodoro design')
console.log('2. Use an online tool like https://www.favicon-generator.org/ to generate sizes:')
console.log('   - icon16.png (16x16)')
console.log('   - icon48.png (48x48)')
console.log('   - icon128.png (128x128)')
console.log('3. Place all three icon files in the dist folder after building')
console.log('\nAlternatively, you can use ImageMagick or similar tools:')
console.log('  convert icon128.png -resize 48x48 icon48.png')
console.log('  convert icon128.png -resize 16x16 icon16.png')





