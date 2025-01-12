from src.dependencies import check_dependencies


if __name__ == "__main__":
    check_dependencies()
    
    from src.bot import update_all
    update_all()