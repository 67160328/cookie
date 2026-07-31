$d = [System.Environment]::GetFolderPath('Desktop')
Get-ChildItem $d | Where-Object { $_.Name -like '*Freecame*' } | Select-Object Name, LastWriteTime
