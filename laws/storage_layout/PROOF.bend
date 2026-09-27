import Base
import ./main.bend as Policy
import ./LAWS.bend as Laws

def Laws.current_dir_is_inbe_everywhere(platform):
  match platform:
    case Policy.Android{}:
      {==}
    case Policy.Web{}:
      {==}
    case Policy.Windows{}:
      {==}
    case Policy.Posix{}:
      {==}

def Laws.current_db_is_inbe():
  {==}

def Laws.legacy_dirs_differ_from_current(platform):
  match platform:
    case Policy.Android{}:
      {==}
    case Policy.Web{}:
      {==}
    case Policy.Windows{}:
      {==}
    case Policy.Posix{}:
      {==}

def Laws.legacy_db_is_breathing():
  {==}

def Laws.export_entry_is_importable():
  {==}

def Laws.historical_entries_stay_importable(entry):
  match entry:
    case Policy.InbeDataDb{}:
      {==}
    case Policy.BreathingDataDb{}:
      {==}
