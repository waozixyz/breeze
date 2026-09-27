import Base

type Platform is Data:
  Android{}
  Web{}
  Windows{}
  Posix{}

type DirName is Data:
  Inbe{}
  Breathing{}
  BreathSession{}

type DbName is Data:
  InbeDb{}
  BreathingDb{}

type Same is Data:
  Different{}
  Same{}

type EntryName is Data:
  InbeDataDb{}
  BreathingDataDb{}

type Importable is Data:
  Yes{}

def current_dir(platform: Platform) -> DirName:
  match platform:
    case Android{}:
      Inbe{}
    case Web{}:
      Inbe{}
    case Windows{}:
      Inbe{}
    case Posix{}:
      Inbe{}

def current_db() -> DbName:
  InbeDb{}

def legacy_dir(platform: Platform) -> DirName:
  match platform:
    case Android{}:
      Breathing{}
    case Web{}:
      Breathing{}
    case Windows{}:
      BreathSession{}
    case Posix{}:
      Breathing{}

def dirs_distinct(current: DirName, legacy: DirName) -> Same:
  match current:
    case Inbe{}:
      match legacy:
        case Inbe{}:
          Same{}
        case Breathing{}:
          Different{}
        case BreathSession{}:
          Different{}
    case Breathing{}:
      match legacy:
        case Inbe{}:
          Different{}
        case Breathing{}:
          Same{}
        case BreathSession{}:
          Different{}
    case BreathSession{}:
      match legacy:
        case Inbe{}:
          Different{}
        case Breathing{}:
          Different{}
        case BreathSession{}:
          Same{}

def legacy_db() -> DbName:
  BreathingDb{}

def export_entry() -> EntryName:
  InbeDataDb{}

def importable(entry: EntryName) -> Importable:
  match entry:
    case InbeDataDb{}:
      Yes{}
    case BreathingDataDb{}:
      Yes{}
